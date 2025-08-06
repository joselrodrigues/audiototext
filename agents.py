from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict
from openai import OpenAI
import requests
import json
import re
from pathlib import Path
import os
from datetime import datetime
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
import signal
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, quote
from enhanced_academic_scraper import EnhancedAcademicScraper

# Load environment variables
load_dotenv()

# Configuration from environment variables
BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')

if not BASE_URL or not API_KEY:
    print("Error: Please set BASE_URL and API_KEY in your .env file")
    sys.exit(1)

# MCP Client for web search
mcp_client = None

# Global flag for interruption
processing_interrupted = False

def signal_handler(signum, frame):
    """Handle Ctrl+C interruption"""
    global processing_interrupted, mcp_client
    processing_interrupted = True
    print("\n\n⚠️  Processing interrupted by user (Ctrl+C)")
    print("Shutting down immediately...")
    
    # Close MCP client if it exists
    if mcp_client:
        try:
            # Force close without waiting
            asyncio.create_task(mcp_client.close())
        except:
            pass
    
    # Exit immediately
    sys.exit(0)
    
# Register signal handler
signal.signal(signal.SIGINT, signal_handler)


def sanitize_error_message(error_msg):
    """Remove sensitive information from error messages"""
    error_str = str(error_msg)[:500]  # Limit length
    # Remove potential API keys, tokens, etc.
    patterns = [
        r'(api[_-]?key|token|bearer|authorization|password|secret)[^\s]*',
        r'Bearer\s+[^\s]+',
        r'https?://[^\s]*@[^\s]+',  # URLs with credentials
        r'[a-zA-Z0-9+/]{40,}',  # Long base64 strings that might be keys
    ]
    for pattern in patterns:
        error_str = re.sub(pattern, '[REDACTED]', error_str, flags=re.IGNORECASE)
    return error_str


def validate_url(url):
    """Validate URL for security before passing to MCP client."""
    # Check if URL is a string
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    
    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")
    
    # Only allow HTTP/HTTPS protocols
    if parsed.scheme not in ['http', 'https']:
        raise ValueError(f"Invalid protocol: {parsed.scheme}. Only HTTP/HTTPS allowed")
    
    # Reject URLs with potentially dangerous characters
    dangerous_chars = ['\n', '\r', '\x00', '<', '>', '"', '{', '}', '|', '\\', '^', '`']
    for char in dangerous_chars:
        if char in url:
            raise ValueError(f"URL contains dangerous character: {char}")
    
    # Reject javascript: and data: URLs disguised as HTTP
    if 'javascript:' in url.lower() or 'data:' in url.lower():
        raise ValueError("JavaScript and data URLs are not allowed")
    
    # Ensure hostname exists
    if not parsed.netloc:
        raise ValueError("URL must have a valid hostname")
    
    # Limit URL length to prevent buffer overflow attacks
    if len(url) > 2048:
        raise ValueError("URL too long (max 2048 characters)")
    
    return True


def sanitize_search_query(query):
    """Sanitize search query for safe URL construction."""
    # Remove any URL encoding attempts
    query = query.replace('%', '')
    
    # Remove dangerous characters
    safe_query = re.sub(r'[^\w\s\-_.,]', ' ', query)
    
    # Collapse multiple spaces
    safe_query = re.sub(r'\s+', ' ', safe_query).strip()
    
    # Limit length
    if len(safe_query) > 200:
        safe_query = safe_query[:200]
    
    # URL encode the safe query
    return quote(safe_query)

async def setup_mcp_client():
    """Setup MCP client with Playwright server"""
    global mcp_client
    if mcp_client is None:
        try:
            mcp_client = MultiServerMCPClient({
                "playwright": {
                    "command": "npx",
                    "args": ["@playwright/mcp@latest", "--browser=chromium", "--headless"],
                    "transport": "stdio"
                }
            })
            # No need to call connect() - client connects automatically
            print("MCP Playwright client initialized")
        except Exception as e:
            print(f"Failed to setup MCP client: {sanitize_error_message(e)}")
            mcp_client = None
    return mcp_client

class AcademicNoteState(TypedDict):
    transcript_path: str
    transcript_content: str
    title: str
    main_concepts: List[str]
    web_search_results: Dict[str, dict]
    deep_research_results: Dict[str, dict]
    fact_checks: List[dict]
    academic_references: List[dict]
    corrected_explanations: str
    final_note: str
    obsidian_links: List[str]

def extract_and_parse_transcript(state: AcademicNoteState) -> AcademicNoteState:
    """Extract and parse transcript content for academic processing"""
    with open(state["transcript_path"], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title and clean it
    lines = content.split('\n')
    title_line = lines[0] if lines else ""
    title = title_line.replace('# Transcription: ', '').replace('.md', '').replace('# Subtitles: ', '')
    
    # Extract main content (skip metadata section)
    content_start = content.find('---\n') + 4
    if content_start > 3:
        main_content = content[content_start:].strip()
    else:
        main_content = content
    
    state["transcript_content"] = main_content
    state["title"] = title
    return state

def identify_main_concepts(state: AcademicNoteState) -> AcademicNoteState:
    """Identify main academic concepts for deep research"""
    global processing_interrupted
    if processing_interrupted:
        print("  Skipping concept identification due to interruption")
        state["main_concepts"] = []
        return state
        
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    prompt = f"""
    Analyze this educational transcript (lecture/course content) and identify the main concepts.
    Focus on technical terms, theories, algorithms, and key principles taught by the instructor.
    Preserve the educational context - this is teaching content, not a research paper.
    Return exactly 3-7 core concepts, each as a single phrase or term.
    Return only the concepts separated by commas, no explanations.
    
    Educational Transcript:
    {state["transcript_content"][:3000]}...
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        concepts_text = response.choices[0].message.content.strip()
        concepts = [concept.strip() for concept in concepts_text.split(',')]
        state["main_concepts"] = concepts[:7]
        
    except Exception as e:
        error_msg = sanitize_error_message(e)
        print(f"Error identifying concepts: {error_msg}")
        
        # Provide more helpful error messages for common issues
        if "connection" in str(e).lower() or "timed out" in str(e).lower():
            print("\n⚠️  Connection Issue Detected:")
            print("   1. Check that BASE_URL and API_KEY are set in .env file")
            print("   2. Verify the AI service is running and accessible")
            print("   3. Check your internet connection")
            print(f"   4. Current BASE_URL: {BASE_URL[:30]}..." if BASE_URL else "   4. BASE_URL not set!")
            print(f"   5. API_KEY is {'set' if API_KEY else 'NOT set'}")
        
        # Return empty concepts to continue processing
        state["main_concepts"] = []
    
    return state

async def search_academic_sources(state: AcademicNoteState) -> AcademicNoteState:
    """Search academic sources using Enhanced Academic Scraper"""
    print(f"  Starting enhanced academic search for concepts: {', '.join(state['main_concepts'])}")
    
    try:
        # Setup MCP client for Google Scholar scraping
        mcp_client = await setup_mcp_client()
        
        # Initialize enhanced scraper
        async with EnhancedAcademicScraper(mcp_client=mcp_client) as scraper:
            search_results = {}
            
            # Process each concept
            for concept in state["main_concepts"]:
                if processing_interrupted:
                    print("  Academic search interrupted")
                    break
                
                print(f"    🔍 Searching all academic sources for: {concept}")
                
                # Search all sources
                try:
                    results = await scraper.search_all_sources(concept, limit=5)
                    summary = scraper.format_results_summary(results)
                    
                    # Create structured results
                    concept_results = {
                        "concept": concept,
                        "total_papers": summary["total_papers"],
                        "sources": summary["sources"],
                        "top_cited": summary["top_cited"],
                        "recent_papers": summary["recent_papers"],
                        "course_materials": summary["course_materials"],
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Log summary
                    print(f"      ✅ Found {summary['total_papers']} results:")
                    for source, data in summary['sources'].items():
                        if data['count'] > 0:
                            print(f"         - {source}: {data['count']} papers/materials")
                    
                    search_results[concept] = concept_results
                    
                except Exception as e:
                    print(f"      ❌ Error searching for {concept}: {sanitize_error_message(e)}")
                    search_results[concept] = {
                        "concept": concept,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
            
            state["web_search_results"] = search_results
            print(f"  ✅ Completed enhanced academic search for {len(search_results)} concepts")
        
    except Exception as e:
        print(f"  ❌ Error in enhanced academic search: {sanitize_error_message(e)}")
        state["web_search_results"] = {}
    
    return state

def perform_deep_research(state: AcademicNoteState) -> AcademicNoteState:
    """Perform comprehensive deep research on each main concept using search results"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    research_results = {}
    
    for concept in state["main_concepts"]:
        if processing_interrupted:
            print("  Deep research interrupted")
            break
            
        print(f"  Researching: {concept}")
        
        # Extract relevant papers and abstracts from search results
        concept_search_results = state.get("web_search_results", {}).get(concept, {})
        
        # Gather abstracts and key findings
        paper_insights = []
        if "sources" in concept_search_results:
            for source_name, source_data in concept_search_results["sources"].items():
                for paper in source_data.get("papers", []):
                    if isinstance(paper, dict) and paper.get("abstract"):
                        paper_insights.append(f"From {paper.get('title', 'Unknown')}: {paper.get('abstract', '')[:300]}...")
        
        # Include top cited papers
        if "top_cited" in concept_search_results:
            for paper in concept_search_results["top_cited"][:2]:
                if paper.get("abstract"):
                    paper_insights.append(f"Highly cited work: {paper.get('abstract', '')[:200]}...")
        
        # Create enriched context from actual academic sources
        academic_context = "\n\n".join(paper_insights[:5]) if paper_insights else "No specific papers found in search."
        
        # Enhanced research prompt with actual academic findings
        prompt = f"""
        Research "{concept}" to support and validate educational content.
        
        Here are actual academic findings from recent papers:
        {academic_context}
        
        Based on these sources and your knowledge, provide comprehensive educational context:
        
        1. ACCURATE DEFINITION:
           - Clear, correct definition for educational context
           - Incorporate insights from the papers above
           - Fix any potential misconceptions
        
        2. EDUCATIONAL CONTEXT:
           - Why this concept is important in learning
           - How it fits into the broader curriculum
           - Common learning challenges or misconceptions
        
        3. TECHNICAL FOUNDATION:
           - Core principles students need to understand
           - Mathematical foundations when relevant
           - Key algorithms or methodologies mentioned in papers
        
        4. PRACTICAL UNDERSTANDING:
           - Real-world applications that help learning
           - Examples that reinforce the concept
           - Industry relevance for motivation
        
        5. COMMON TOOLS AND IMPLEMENTATIONS:
           - Popular frameworks, software, or tools
           - Standard datasets or resources mentioned in papers
           - Typical methodologies or evaluation approaches
        
        6. LEARNING CONNECTIONS:
           - Related concepts students should know
           - Prerequisites and follow-up topics
           - How this connects to other parts of the course
        
        Synthesize the academic sources with educational best practices.
        Focus on helping students understand the lecture content deeply.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2500
            )
            
            research_results[concept] = {
                "content": response.choices[0].message.content.strip(),
                "papers_analyzed": len(paper_insights),
                "sources_count": concept_search_results.get("total_papers", 0),
                "timestamp": datetime.now().isoformat(),
                "tokens_used": len(response.choices[0].message.content.split())
            }
            
            print(f"    ✅ Deep research completed using {len(paper_insights)} paper abstracts")
            
        except Exception as e:
            print(f"    ❌ Error researching {concept}: {sanitize_error_message(e)}")
            research_results[concept] = {
                "content": f"Deep research needed for {concept} - Error in processing",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    state["deep_research_results"] = research_results
    return state

def fact_check_and_correct(state: AcademicNoteState) -> AcademicNoteState:
    """Fact-check transcript content and correct errors"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    # Combine transcript with research for fact-checking
    research_context = "\n\n".join([
        f"Research on {concept}:\n{data['content']}" 
        for concept, data in state["deep_research_results"].items()
    ])
    
    prompt = f"""
    Fact-check this educational transcript for common transcription errors and technical accuracy.
    This is teaching content, so preserve the instructor's voice, examples, and pedagogical flow.
    
    CRITICAL: Look for common transcription errors such as:
    - Technical terms that sound similar (e.g., "ordinance" → "RNN")
    - Brand/product names that are misheard
    - Academic terminology that gets distorted
    - Dataset or tool names that are mispronounced
    
    Original Educational Transcript:
    {state["transcript_content"]}
    
    Research Context for verification:
    {research_context[:4000]}...
    
    Rules:
    1. Fix obvious transcription errors
    2. Preserve ALL specific examples mentioned by instructor
    3. Keep the teaching style and narrative flow
    4. Don't add information not in the original transcript
    5. Maintain the educational context and progression
    
    Format:
    ## Corrected Content:
    [corrected transcript with fixed errors but preserved teaching style]
    
    ## Corrections Made:
    - [list of transcription errors fixed]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        result = response.choices[0].message.content.strip()
        
        # Extract corrected content and corrections
        if "## Corrected Content:" in result:
            parts = result.split("## Corrections Made:")
            corrected_content = parts[0].replace("## Corrected Content:", "").strip()
            corrections = parts[1].strip() if len(parts) > 1 else "No corrections needed."
        else:
            corrected_content = state["transcript_content"]
            corrections = "Fact-checking completed."
        
        state["corrected_explanations"] = corrected_content
        state["fact_checks"] = [{"corrections": corrections, "timestamp": datetime.now().isoformat()}]
        
    except Exception as e:
        print(f"Error fact-checking: {sanitize_error_message(e)}")
        state["corrected_explanations"] = state["transcript_content"]
        state["fact_checks"] = [{"corrections": "Error in fact-checking process."}]
    
    return state

def find_academic_references(state: AcademicNoteState) -> AcademicNoteState:
    """Find and consolidate academic references from enhanced search results"""
    print(f"  Consolidating academic references from search results")
    
    references = []
    all_papers = []
    all_course_materials = []
    
    # Extract all papers and materials from search results
    for concept, results in state.get("web_search_results", {}).items():
        if "error" in results:
            continue
            
        # Collect papers from all sources
        for source_name, source_data in results.get("sources", {}).items():
            for paper in source_data.get("papers", []):
                paper_dict = paper if isinstance(paper, dict) else paper.to_dict()
                paper_dict["concept_related"] = concept
                all_papers.append(paper_dict)
        
        # Collect course materials
        for material in results.get("course_materials", []):
            material_dict = material if isinstance(material, dict) else material.to_dict()
            material_dict["concept_related"] = concept
            all_course_materials.append(material_dict)
    
    # Create book references from papers with high citations
    books_refs = []
    highly_cited = sorted([p for p in all_papers if p.get("citations", 0) > 100], 
                         key=lambda x: x.get("citations", 0), reverse=True)
    
    # Create paper references categorized by age
    recent_papers = [p for p in all_papers if p.get("year", 0) >= 2022]
    seminal_papers = [p for p in all_papers if p.get("year", 0) < 2022 and p.get("citations", 0) > 50]
    
    # Format references
    # Add course materials as online resources
    for material in all_course_materials[:5]:
        references.append({
            "type": "online resources",
            "citation": f"{material.get('title', 'Unknown')} - {material.get('abstract', 'Course material')}. URL: {material.get('url', '')}",
            "concept_related": material.get("concept_related", ""),
            "source": material.get("source", ""),
            "timestamp": datetime.now().isoformat()
        })
    
    # Add seminal papers
    for paper in seminal_papers[:6]:
        authors = paper.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        citation = f"{author_str} ({paper.get('year', 'N/A')}). {paper.get('title', 'Unknown')}."
        
        if paper.get("venue"):
            citation += f" {paper.get('venue')}."
        if paper.get("doi"):
            citation += f" DOI: {paper.get('doi')}"
        elif paper.get("arxiv_id"):
            citation += f" arXiv: {paper.get('arxiv_id')}"
            
        references.append({
            "type": "seminal research papers",
            "citation": citation,
            "concept_related": paper.get("concept_related", ""),
            "source": paper.get("source", ""),
            "citations_count": paper.get("citations", 0),
            "timestamp": datetime.now().isoformat()
        })
    
    # Add recent papers
    for paper in recent_papers[:3]:
        authors = paper.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        citation = f"{author_str} ({paper.get('year', 'N/A')}). {paper.get('title', 'Unknown')}."
        
        if paper.get("venue"):
            citation += f" {paper.get('venue')}."
        if paper.get("url"):
            citation += f" Available: {paper.get('url')}"
            
        references.append({
            "type": "recent developments",
            "citation": citation,
            "concept_related": paper.get("concept_related", ""),
            "source": paper.get("source", ""),
            "timestamp": datetime.now().isoformat()
        })
    
    # Also use LLM to suggest foundational books (since APIs don't return books)
    concepts_list = ", ".join(state["main_concepts"])
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    try:
        prompt = f"""Based on these concepts: {concepts_list}
        
        Suggest 3-4 REAL foundational textbooks that students should read.
        Format each as:
        - Author(s) (Year). Title. Publisher. ISBN.
        
        Only suggest well-known, actually published academic textbooks."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        book_text = response.choices[0].message.content.strip()
        for line in book_text.split('\n'):
            if line.strip().startswith('-'):
                references.append({
                    "type": "foundational books",
                    "citation": line.strip()[2:],
                    "concept_related": concepts_list,
                    "timestamp": datetime.now().isoformat()
                })
                
    except Exception as e:
        print(f"  Error getting book suggestions: {sanitize_error_message(e)}")
    
    state["academic_references"] = references
    print(f"  ✅ Consolidated {len(references)} academic references from enhanced search")
    
    # Log summary by type
    ref_types = {}
    for ref in references:
        ref_type = ref.get("type", "unknown")
        ref_types[ref_type] = ref_types.get(ref_type, 0) + 1
    
    for ref_type, count in ref_types.items():
        print(f"     - {ref_type}: {count}")
    
    return state

def generate_obsidian_note(state: AcademicNoteState) -> AcademicNoteState:
    """Generate comprehensive academic note with enhanced educational structure"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    print(f"  Generating enhanced educational note with new structure")
    
    # Organize references by type with better parsing
    books = [ref["citation"] for ref in state["academic_references"] if "book" in ref["type"]]
    online_resources = [ref["citation"] for ref in state["academic_references"] if "online" in ref["type"]]
    papers = [ref["citation"] for ref in state["academic_references"] if "paper" in ref["type"]]
    recent_developments = [ref["citation"] for ref in state["academic_references"] if "recent" in ref["type"]]
    
    # Prepare detailed research content with abstracts
    detailed_research = ""
    paper_abstracts = []
    
    for concept, data in state["deep_research_results"].items():
        detailed_research += f"\n\n### Deep Analysis: {concept}\n{data['content']}"
        
        # Extract paper abstracts if available
        papers_count = data.get("papers_analyzed", 0)
        if papers_count > 0:
            paper_abstracts.append(f"{concept}: {papers_count} papers analyzed")
    
    # Extract course materials and top cited papers
    course_materials = []
    top_papers = []
    
    for concept, results in state.get("web_search_results", {}).items():
        if isinstance(results, dict):
            # Extract course materials
            for material in results.get("course_materials", []):
                if isinstance(material, dict):
                    course_materials.append(material)
            
            # Extract top cited papers
            for paper in results.get("top_cited", []):
                if isinstance(paper, dict) and paper.get("citations", 0) > 50:
                    top_papers.append(paper)
    
    # Enhanced prompt for rich Markdown formatting and structure
    prompt = f"""
    Create a comprehensive educational note with RICH VISUAL FORMATTING for university students.
    Use ADVANCED MARKDOWN features for engaging, visually appealing content.
    
    CONTEXT:
    Title: {state["title"]} (Educational Content)
    Main Concepts: {", ".join(state["main_concepts"])}
    Academic Papers Analyzed: {len(paper_abstracts)} concepts with research
    Course Materials Found: {len(course_materials)} university resources
    
    ORIGINAL TEACHING CONTENT:
    {state["corrected_explanations"][:3500]}
    
    ACADEMIC RESEARCH INSIGHTS:
    {detailed_research[:3500]}
    
    FORMATTING REQUIREMENTS - Use These Rich Markdown Features:
    
    1. **Callout Boxes** - Use for important concepts:
    > [!NOTE] Important Concept
    > Key learning point here
    
    > [!WARNING] Common Misconception  
    > What students often get wrong
    
    > [!TIP] Pro Tip
    > Advanced insight or technique
    
    > [!EXAMPLE] Example
    > Concrete example demonstration
    
    2. **Mathematical Formulas** - Use proper LaTeX blocks:
    $$h_t = f(W_h \cdot h_{{t-1}} + W_x \cdot x_t + b)$$
    
    3. **Rich Tables** with emojis and visual structure
    
    4. **Visual Separators** and hierarchical headers with emojis
    
    5. **Code blocks** with syntax highlighting when appropriate
    
    6. **Obsidian Internal Links** like [[Concept Name]] for cross-references
    
    ENHANCED STRUCTURE WITH RICH FORMATTING:
    
    # 🎓 {state["title"]} - Comprehensive Study Notes
    
    ---
    
    ## 🎯 Learning Objectives
    > [!NOTE] What You'll Master
    > By the end of this study session, you will:
    > - [Extract key learning outcomes from content]
    > - [Connect concepts to practical applications]
    > - [Build foundational knowledge for advanced topics]
    
    ---
    
    ## 📚 Prerequisites & Context
    
    > [!TIP] Before You Begin
    > **Prerequisites**: [What students need to know]
    > **Difficulty Level**: [Beginner/Intermediate/Advanced]
    > **Time Investment**: [Estimated study time]
    
    **🎯 Curriculum Fit**: [How this fits in the broader learning path]
    
    ---
    
    ## 📖 Course Context & Overview
    
    > [!EXAMPLE] Real-World Relevance
    > [Why this topic matters in industry/research]
    
    [Rich overview with visual structure]
    
    ---
    
    ## 🔬 Key Concepts Deep Dive
    
    For each concept, use this rich structure:
    
    ### 🧠 [Concept Name]
    
    > [!NOTE] Core Definition
    > [Clear, precise definition with academic backing]
    
    #### 🎯 Theory & Fundamentals
    [Detailed explanation with visual metaphors]
    
    #### ⚠️ Common Misconceptions
    > [!WARNING] Students Often Think...
    > [What students get wrong and why]
    
    #### 💡 Visual Understanding
    > [!TIP] Think of it Like This
    > [Concrete analogies and visual metaphors]
    
    #### 🔢 Mathematical Foundation
    [Use LaTeX blocks for formulas]:
    $$[relevant formulas with proper notation]$$
    
    Where:
    - Variable₁ = [definition]
    - Variable₂ = [definition]
    
    ---
    
    ## 🎬 Instructor Examples & Demonstrations
    
    > [!EXAMPLE] Live Demonstration
    > [ALL original examples preserved exactly with rich formatting]
    
    ---
    
    ## ⚙️ Technical Implementation Details
    
    > [!NOTE] Technical Specs
    > [Enhanced with research findings in structured format]
    
    ```python
    # Code examples when relevant
    [formatted code blocks]
    ```
    
    ---
    
    ## 🛠️ Tools & Resources
    
    | Tool/Framework | Purpose | Key Features |
    |---------------|---------|-------------|
    | [Tool Name] | [What it does] | [Why it's useful] |
    
    ---
    
    ## 🌍 Real-World Applications
    
    > [!EXAMPLE] Industry Applications
    > 1. **[Application Area]**: [How it's used]
    > 2. **[Application Area]**: [Practical impact]
    > 3. **[Application Area]**: [Market relevance]
    
    ---
    
    ## 🔬 Deep Dive Research
    
    ### 📄 Key Academic Papers
    > [!NOTE] Essential Reading
    > [Top 3-5 papers with abstracts and key findings]
    
    ### 🎓 University Course Materials  
    > [!TIP] Additional Learning Resources
    > [MIT OCW, Stanford resources with direct links]
    
    ### 🆕 Recent Developments (2022-2025)
    > [!EXAMPLE] Cutting-Edge Research
    > [Latest breakthroughs and their implications]
    
    ---
    
    ## 💻 Implementation Guide
    
    > [!TIP] Getting Started
    > [Step-by-step technical implementation notes]
    
    ```bash
    # Terminal commands when relevant
    [formatted command examples]
    ```
    
    ---
    
    ## 🔗 Related Concepts Network
    
    ```mermaid
    graph TD
        A[{state["main_concepts"][0] if state["main_concepts"] else "Main Topic"}] --> B[Prerequisite Concept]
        A --> C[Related Concept]
        A --> D[Advanced Topic]
    ```
    
    **Learning Path**: [[Previous Topic]] → **Current Topic** → [[Next Topic]]
    
    ---
    
    ## 🎓 Interactive Study Guide
    
    ### 🤔 Self-Assessment Questions
    > [!NOTE] Test Your Understanding
    > 1. **Concept Check**: Can you explain [key concept] without looking?
    > 2. **Application**: How would you apply [concept] to solve [real problem]?
    > 3. **Connections**: What's the relationship between [concept A] and [concept B]?
    
    ### 📝 Practice Problems
    
    > [!EXAMPLE] Beginner Level
    > **Challenge**: [Simple application problem]
    > **Goal**: [What they should learn]
    
    > [!TIP] Intermediate Level  
    > **Challenge**: [More complex scenario]
    > **Skills**: [What they should demonstrate]
    
    > [!WARNING] Advanced Level
    > **Challenge**: [Research or implementation challenge]
    > **Outcome**: [Professional-level competency]
    
    ### 🚀 Mini Project Ideas
    - **📱 Project 1**: [Practical implementation exercise]
    - **🔬 Project 2**: [Research-based exploration]
    - **🎯 Project 3**: [Real-world application challenge]
    
    ---
    
    ## 📊 Quick Reference Card
    
    | 🎯 Concept | 📝 Definition | ⚡ Key Formula/Point | 🔗 Links |
    |------------|---------------|---------------------|----------|
    | [Concept 1] | [Brief definition] | [Formula/Key point] | [[Related Topic]] |
    | [Concept 2] | [Brief definition] | [Formula/Key point] | [[Related Topic]] |
    
    ---
    
    ## 📚 Deep Dive References
    
    ### 📖 Foundational Books
    {chr(10).join(f"> 📚 {book}" for book in books)}
    
    ### 🌐 Online Resources
    {chr(10).join(f"> 🔗 {resource}" for resource in online_resources)}
    
    ### 🔬 Research Papers
    {chr(10).join(f"> 📄 {paper}" for paper in papers)}
    
    ### 🆕 Recent Developments  
    {chr(10).join(f"> ⚡ {dev}" for dev in recent_developments)}
    
    ---
    
    ## ✅ Mastery Checklist
    
    > [!NOTE] Learning Milestones
    > - [ ] I can define all key concepts clearly
    > - [ ] I understand the practical applications
    > - [ ] I can solve basic problems independently  
    > - [ ] I see connections to other topics
    > - [ ] I'm ready for advanced material
    
    ## 🏷️ Tags
    #{" #".join([concept.lower().replace(" ", "-") for concept in state["main_concepts"]])} #comprehensive-study #university-level #enhanced-notes #visual-learning
    
    ---
    *📅 Enhanced on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} using o3-mini*  
    *🎯 Original concepts: {", ".join(state["main_concepts"])}*  
    *📊 Related materials: {len(course_materials) + len(paper_abstracts)} items*
    
    CRITICAL INSTRUCTIONS:
    1. Use ALL the rich formatting features shown above
    2. Make it visually engaging with emojis, callouts, and tables
    3. Preserve 85% original content, enhance with 15% visual structure
    4. Focus on university-level depth with engaging presentation
    5. Use Obsidian-compatible syntax throughout
    """
    
    try:
        response = client.chat.completions.create(
            model="o3-mini",  # Changed to o3-mini for better final generation
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Lower for more structured output
            max_tokens=4500   # Increased for enhanced content
        )
        
        final_note = response.choices[0].message.content.strip()
        
        # Extract Obsidian links for tracking
        obsidian_links = re.findall(r'\[\[([^\]]+)\]\]', final_note)
        
        state["final_note"] = final_note
        state["obsidian_links"] = list(set(obsidian_links))
        
        print(f"  ✅ Generated enhanced educational note:")
        print(f"     - {len(obsidian_links)} cross-references")
        print(f"     - {len(course_materials)} course materials integrated")
        print(f"     - {len(top_papers)} top papers included")
        print(f"     - Enhanced structure with study guide")
        
    except Exception as e:
        print(f"  ❌ Error generating enhanced note: {sanitize_error_message(e)}")
        state["final_note"] = f"# {state['title']}\n\nError generating enhanced academic note: {str(e)}"
        state["obsidian_links"] = []
    
    return state

def create_academic_note_workflow():
    """Create the LangGraph workflow for academic note generation"""
    workflow = StateGraph(AcademicNoteState)
    
    # Add nodes
    workflow.add_node("extract_transcript", extract_and_parse_transcript)
    workflow.add_node("identify_concepts", identify_main_concepts)
    workflow.add_node("web_search", search_academic_sources)
    workflow.add_node("deep_research", perform_deep_research)
    workflow.add_node("fact_check", fact_check_and_correct)
    workflow.add_node("find_references", find_academic_references)
    workflow.add_node("generate_note", generate_obsidian_note)
    
    # Define edges
    workflow.set_entry_point("extract_transcript")
    workflow.add_edge("extract_transcript", "identify_concepts")
    workflow.add_edge("identify_concepts", "web_search")
    workflow.add_edge("web_search", "deep_research")
    workflow.add_edge("deep_research", "fact_check")
    workflow.add_edge("fact_check", "find_references")
    workflow.add_edge("find_references", "generate_note")
    workflow.add_edge("generate_note", END)
    
    return workflow.compile()

async def process_transcript_to_academic_note_async(transcript_path: str, output_dir: str = "knowledge_base"):
    """Async version of transcript processing with MCP integration"""
    if not os.path.exists(transcript_path):
        print(f"Error: Transcript file not found: {transcript_path}")
        return None
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create initial state
    initial_state = AcademicNoteState(
        transcript_path=transcript_path,
        transcript_content="",
        title="",
        main_concepts=[],
        web_search_results={},
        deep_research_results={},
        fact_checks=[],
        academic_references=[],
        corrected_explanations="",
        final_note="",
        obsidian_links=[]
    )
    
    # Create and run workflow
    print(f"Processing transcript: {transcript_path}")
    workflow = create_academic_note_workflow()
    
    try:
        final_state = await workflow.ainvoke(initial_state)
        
        # Generate output filename preserving folder structure
        base_name = os.path.splitext(os.path.basename(transcript_path))[0]
        # Clean filename for better organization
        clean_name = re.sub(r'[^\w\s-]', '', base_name.lower())
        clean_name = re.sub(r'[\s]+', '-', clean_name)
        
        # Preserve the folder structure from transcripts to knowledge_base
        transcript_dir = os.path.dirname(transcript_path)
        # Get the relative path from transcripts folder
        if "transcripts" in transcript_dir:
            rel_path = os.path.relpath(transcript_dir, "transcripts")
            if rel_path != ".":
                # Create the corresponding directory structure in knowledge_base
                course_output_dir = os.path.join(output_dir, rel_path)
                os.makedirs(course_output_dir, exist_ok=True)
                output_path = os.path.join(course_output_dir, f"{clean_name}.md")
            else:
                output_path = os.path.join(output_dir, f"{clean_name}.md")
        else:
            output_path = os.path.join(output_dir, f"{clean_name}.md")
        
        # Save academic note
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_state["final_note"])
        
        print(f"Academic note saved to: {output_path}")
        print(f"Concepts covered: {', '.join(final_state['main_concepts'])}")
        print(f"Obsidian links created: {', '.join(final_state['obsidian_links'])}")
        
        return final_state
        
    except Exception as e:
        print(f"Error processing transcript: {sanitize_error_message(e)}")
        return None

def test_llm_connection():
    """Test connection to LLM service"""
    try:
        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10
        )
        return True
    except Exception as e:
        print(f"\n❌ Failed to connect to LLM service: {sanitize_error_message(e)}")
        print(f"   BASE_URL: {BASE_URL}")
        print(f"   Make sure the service is running and accessible")
        return False

def process_transcript_to_academic_note(transcript_path: str, output_dir: str = "knowledge_base"):
    """Sync wrapper for transcript processing with MCP integration"""
    return asyncio.run(process_transcript_to_academic_note_async(transcript_path, output_dir))

def check_existing_note(transcript_path: str, output_dir: str = "knowledge_base") -> str:
    """Check if a knowledge note already exists for a transcript."""
    transcript_file_path = Path(transcript_path)
    
    # Extract base name and clean it
    base_name = transcript_file_path.stem
    clean_name = base_name.replace('-subtitles', '').replace('_subtitles', '')
    
    # Build expected output path preserving folder structure
    if "transcripts" in str(transcript_file_path.parent):
        rel_path = os.path.relpath(transcript_file_path.parent, "transcripts")
        if rel_path != ".":
            course_output_dir = os.path.join(output_dir, rel_path)
            expected_note_path = os.path.join(course_output_dir, f"{clean_name}.md")
        else:
            expected_note_path = os.path.join(output_dir, f"{clean_name}.md")
    else:
        expected_note_path = os.path.join(output_dir, f"{clean_name}.md")
    
    return expected_note_path if os.path.exists(expected_note_path) else None

def ask_user_confirmation(message, default="n"):
    """Ask user for confirmation with a default option."""
    valid_responses = {"y": True, "yes": True, "n": False, "no": False}
    prompt = f"{message} [y/N]: " if default == "n" else f"{message} [Y/n]: "
    
    while True:
        try:
            response = input(prompt).lower().strip()
            if not response:
                return valid_responses[default]
            if response in valid_responses:
                return valid_responses[response]
            print("Please answer with 'y' or 'n' (or 'yes' or 'no').")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return False

def batch_process_transcripts(transcripts_dir: str = "transcripts", output_dir: str = "knowledge_base", force_mode: bool = False):
    """Process all transcript files in a directory including subtitles"""
    # Test LLM connection before processing
    print("Testing connection to LLM service...")
    if not test_llm_connection():
        print("\n❌ Cannot proceed without LLM connection. Please check your configuration.")
        return
    print("✅ LLM connection successful!\n")
    
    if force_mode:
        print("🔄 Force mode: Will overwrite existing notes without asking\n")
    
    transcript_files = []
    
    # Find all markdown files in transcripts directory (including subtitles)
    for root, dirs, files in os.walk(transcripts_dir):
        for file in files:
            if file.endswith('.md'):  # Include both regular and subtitle transcripts
                transcript_files.append(os.path.join(root, file))
    
    # Sort files for consistent processing order
    transcript_files.sort()
    
    print(f"Found {len(transcript_files)} transcript files to process")
    for i, file in enumerate(transcript_files, 1):
        print(f"  {i}. {file}")
    
    processed_successfully = 0
    skipped = 0
    
    for transcript_file in transcript_files:
        if processing_interrupted:
            print("\n\n🛑 Batch processing interrupted by user")
            break
        
        # Check if note already exists
        existing_note = check_existing_note(transcript_file, output_dir)
        
        if existing_note:
            print(f"\n📄 Note already exists for '{os.path.basename(transcript_file)}':")
            print(f"  - {os.path.relpath(existing_note)}")
            
            if force_mode or ask_user_confirmation(f"Do you want to re-process '{os.path.basename(transcript_file)}'?"):
                if force_mode:
                    print(f"\n🔄 Force re-processing ({processed_successfully + 1}/{len(transcript_files)}): {transcript_file}")
                else:
                    print(f"\n🔄 Re-processing ({processed_successfully + 1}/{len(transcript_files)}): {transcript_file}")
                result = process_transcript_to_academic_note(transcript_file, output_dir)
                if result:
                    processed_successfully += 1
                else:
                    print(f"Failed to process: {transcript_file}")
            else:
                print(f"⏭️  Skipping {os.path.basename(transcript_file)}")
                skipped += 1
        else:
            print(f"\n📝 Processing ({processed_successfully + 1}/{len(transcript_files)}): {transcript_file}")
            result = process_transcript_to_academic_note(transcript_file, output_dir)
            if result:
                processed_successfully += 1
            else:
                print(f"Failed to process: {transcript_file}")
    
    print(f"\n=== Batch Processing {'Interrupted' if processing_interrupted else 'Complete'} ===")
    print(f"Successfully processed: {processed_successfully}/{len(transcript_files)} files")
    print(f"Skipped: {skipped} files")
    if processing_interrupted:
        remaining = len(transcript_files) - processed_successfully - skipped
        print(f"Interrupted: {remaining} files not processed due to interruption")
    print(f"Academic notes saved in: {output_dir}/")

if __name__ == "__main__":
    # Example usage
    import sys
    
    # Check for force flag
    force_mode = '--force' in sys.argv
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch" or "batch" in sys.argv:
            batch_process_transcripts(force_mode=force_mode)
        else:
            transcript_file = sys.argv[1]
            # Validate the file path before processing
            if not os.path.exists(transcript_file):
                print(f"Error: File not found: {transcript_file}")
                sys.exit(1)
            if not transcript_file.endswith('.md'):
                print(f"Error: Expected .md file, got: {transcript_file}")
                sys.exit(1)
            # Ensure file is within allowed directories
            abs_path = os.path.abspath(transcript_file)
            allowed_dirs = [os.path.abspath('transcripts'), os.path.abspath('.')]
            if not any(abs_path.startswith(d + os.sep) or abs_path == d for d in allowed_dirs):
                print(f"Error: File must be in transcripts directory or current directory")
                sys.exit(1)
            process_transcript_to_academic_note(transcript_file)
    else:
        # Process a single file for testing
        test_file = "transcripts/machine-learning-course/001-human-activity-recognition.md"
        if os.path.exists(test_file):
            process_transcript_to_academic_note(test_file)
        else:
            print("No test file found. Run with 'batch' argument to process all transcripts.")