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
    """Search academic sources using Playwright MCP for real web data"""
    print(f"  Starting web search for concepts: {', '.join(state['main_concepts'])}")
    
    try:
        client = await setup_mcp_client()
        if client is None:
            print("  MCP client not available, skipping web search")
            state["web_search_results"] = {}
            return state

        search_results = {}
        
        # Get tools from all connected servers
        try:
            tools = await client.get_tools()
            print(f"  Found {len(tools)} tools from MCP servers")
            
            # Print available tools for debugging
            for tool in tools:
                print(f"    Tool: {tool.name} - {tool.description[:50]}...")
            
            # Check if browser needs to be installed
            install_tool = None
            for tool in tools:
                if tool.name == 'browser_install':
                    install_tool = tool
                    break
            
            if install_tool:
                print("  Installing browser...")
                try:
                    await install_tool.ainvoke({})
                    print("  Browser installed successfully")
                except Exception as e:
                    print(f"  Warning: Could not install browser: {e}")
                    
        except Exception as e:
            print(f"  Error getting tools from MCP: {sanitize_error_message(e)}")
            state["web_search_results"] = {}
            return state
        
        # Process each concept
        for concept in state["main_concepts"]:
            if processing_interrupted:
                print("  Web search interrupted")
                break
                
            print(f"    Searching web for: {concept}")
            
            concept_results = {
                "concept": concept,
                "scholar_results": [],
                "arxiv_results": [],
                "university_results": [],
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                # Look for browser navigation and snapshot tools
                navigate_tool = None
                snapshot_tool = None
                
                for tool in tools:
                    if tool.name == 'browser_navigate':
                        navigate_tool = tool
                    elif tool.name == 'browser_snapshot':
                        snapshot_tool = tool
                
                if navigate_tool and snapshot_tool:
                    print(f"    Using tools: {navigate_tool.name} and {snapshot_tool.name}")
                    
                    # Sanitize concept for URL construction
                    safe_concept = sanitize_search_query(concept)
                    
                    # Search Google Scholar
                    scholar_url = f"https://scholar.google.com/scholar?q={safe_concept}"
                    
                    # Validate URL before using
                    try:
                        validate_url(scholar_url)
                    except ValueError as e:
                        print(f"    Invalid URL for Google Scholar: {e}")
                        continue
                    
                    # Navigate to Google Scholar
                    try:
                        nav_result = await navigate_tool.ainvoke({"url": scholar_url})
                    except Exception as e:
                        print(f"    Failed to navigate to Google Scholar: {sanitize_error_message(e)}")
                        nav_result = None
                    
                    # Get page snapshot
                    snapshot_result = await snapshot_tool.ainvoke({})
                    
                    concept_results["scholar_results"] = [
                        {
                            "source": "Google Scholar",
                            "content": str(snapshot_result)[:1000] if snapshot_result else "No content extracted",
                            "url": scholar_url
                        }
                    ]
                    
                    # Search arXiv
                    arxiv_url = f"https://arxiv.org/search/?query={safe_concept}&searchtype=all"
                    
                    # Validate URL before using
                    try:
                        validate_url(arxiv_url)
                    except ValueError as e:
                        print(f"    Invalid URL for arXiv: {e}")
                        concept_results["arxiv_results"] = []
                        results[concept] = concept_results
                        continue
                    
                    try:
                        nav_result = await navigate_tool.ainvoke({"url": arxiv_url})
                    except Exception as e:
                        print(f"    Failed to navigate to arXiv: {sanitize_error_message(e)}")
                        nav_result = None
                    snapshot_result = await snapshot_tool.ainvoke({})
                    
                    concept_results["arxiv_results"] = [
                        {
                            "source": "arXiv",
                            "content": str(snapshot_result)[:1000] if snapshot_result else "No content extracted",
                            "url": arxiv_url
                        }
                    ]
                    
                else:
                    print(f"    Required navigation/content tools not found")
                    # Fallback to placeholder results
                    concept_results["status"] = "MCP tools not available - using placeholder"
                    
            except Exception as e:
                print(f"    Error searching for {concept}: {sanitize_error_message(e)}")
                concept_results["error"] = str(e)
            
            search_results[concept] = concept_results
            
        state["web_search_results"] = search_results
        print(f"  Completed web search for {len(search_results)} concepts")
        
    except Exception as e:
        print(f"Error in web search: {sanitize_error_message(e)}")
        state["web_search_results"] = {}
    
    return state

def perform_deep_research(state: AcademicNoteState) -> AcademicNoteState:
    """Perform comprehensive deep research on each main concept"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    research_results = {}
    
    for concept in state["main_concepts"]:
        if processing_interrupted:
            print("  Deep research interrupted")
            break
            
        print(f"  Researching: {concept}")
        
        # Enhanced research prompt with specific focus areas
        prompt = f"""
        Research "{concept}" to support and validate educational content.
        Focus on information that helps understand and enhance what was taught in the lecture.
        
        Provide contextual information including:
        
        1. ACCURATE DEFINITION:
           - Clear, correct definition for educational context
           - Fix any potential misconceptions from transcription errors
        
        2. EDUCATIONAL CONTEXT:
           - Why this concept is important in learning
           - How it fits into the broader curriculum
           - Common learning challenges or misconceptions
        
        3. TECHNICAL FOUNDATION:
           - Core principles students need to understand
           - Mathematical foundations when relevant
           - Key algorithms or methodologies
        
        4. PRACTICAL UNDERSTANDING:
           - Real-world applications that help learning
           - Examples that reinforce the concept
           - Industry relevance for motivation
        
        5. COMMON TOOLS AND IMPLEMENTATIONS:
           - Popular frameworks, software, or tools relevant to this field
           - Standard datasets, resources, or materials commonly used
           - Typical methodologies or evaluation approaches
        
        6. LEARNING CONNECTIONS:
           - Related concepts students should know
           - Prerequisites and follow-up topics
           - How this connects to other parts of the course
        
        Focus on educational value and accuracy rather than cutting-edge research.
        Prioritize information that helps students understand the lecture content.
        Avoid adding complex details not relevant to the subject matter or educational level presented.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower temperature for more factual content
                max_tokens=2000   # Increased for more detailed responses
            )
            
            research_results[concept] = {
                "content": response.choices[0].message.content.strip(),
                "timestamp": datetime.now().isoformat(),
                "tokens_used": len(response.choices[0].message.content.split())
            }
            
        except Exception as e:
            print(f"Error researching {concept}: {sanitize_error_message(e)}")
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
    """Find comprehensive and specific academic references"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    concepts_list = ", ".join(state["main_concepts"])
    
    print(f"  Finding academic references for: {concepts_list}")
    
    # Enhanced prompt for more specific and realistic references
    prompt = f"""
    Find comprehensive, REAL academic references for these specific concepts: {concepts_list}
    
    Requirements:
    1. AUTHORITATIVE BOOKS - Provide 3-5 real, well-known academic books with:
       - Complete citation (Author(s), Title, Publisher, Year, ISBN if known)
       - Brief description of relevance to the concepts
       - Edition information where applicable
    
    2. HIGH-QUALITY ONLINE RESOURCES - Provide 4-6 real, authoritative URLs:
       - University course materials and lecture notes
       - Official documentation and technical specifications
       - Professional organization resources
       - Government or institutional research repositories
       - Include specific URL and detailed description
    
    3. SEMINAL RESEARCH PAPERS - Provide 4-6 key academic papers:
       - Complete citation with journal name, volume, pages
       - DOI or arXiv ID where available
       - Brief summary of contribution to the field
       - Publication year (mix of foundational and recent works)
    
    4. RECENT DEVELOPMENTS - Include 2-3 very recent papers (2022-2025):
       - Focus on latest advances and current research
       - Conference proceedings from top-tier venues
       - Include impact and significance
    
    Format exactly as:
    ## Foundational Books
    - [Complete citation with ISBN] - [Relevance description]
    
    ## Online Resources
    - [Complete URL] - [Detailed description of content and authority]
    
    ## Seminal Research Papers
    - [Author(s). (Year). Title. Journal, Volume(Issue), pages. DOI] - [Contribution summary]
    
    ## Recent Developments (2022-2025)
    - [Recent paper citation] - [Impact and significance]
    
    Focus on REAL, VERIFIABLE sources. Include specific details like ISBN, DOI, exact URLs.
    Prioritize highly cited works and authoritative sources.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Very low temperature for factual accuracy
            max_tokens=2500   # Increased for comprehensive references
        )
        
        references_text = response.choices[0].message.content.strip()
        
        # Enhanced parsing for better categorization
        references = []
        current_section = ""
        for line in references_text.split('\n'):
            line = line.strip()
            if line.startswith('## '):
                current_section = line.replace('## ', '').lower()
            elif line.startswith('- ') and current_section:
                citation = line.replace('- ', '').strip()
                if citation:  # Only add non-empty citations
                    references.append({
                        "type": current_section,
                        "citation": citation,
                        "concept_related": concepts_list,
                        "timestamp": datetime.now().isoformat()
                    })
        
        state["academic_references"] = references
        print(f"  Found {len(references)} academic references")
        
    except Exception as e:
        print(f"Error finding references: {sanitize_error_message(e)}")
        state["academic_references"] = [{
            "type": "error",
            "citation": f"Error finding academic references: {str(e)}",
            "concept_related": concepts_list
        }]
    
    return state

def generate_obsidian_note(state: AcademicNoteState) -> AcademicNoteState:
    """Generate comprehensive academic note in Obsidian-compatible format"""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    
    print(f"  Generating comprehensive academic note")
    
    # Organize references by type with better parsing
    books = [ref["citation"] for ref in state["academic_references"] if "book" in ref["type"]]
    online_resources = [ref["citation"] for ref in state["academic_references"] if "online" in ref["type"]]
    papers = [ref["citation"] for ref in state["academic_references"] if "paper" in ref["type"]]
    recent_developments = [ref["citation"] for ref in state["academic_references"] if "recent" in ref["type"]]
    
    # Prepare detailed research content
    detailed_research = ""
    for concept, data in state["deep_research_results"].items():
        detailed_research += f"\n\n### Deep Analysis: {concept}\n{data['content']}"
    
    # Enhanced prompt for comprehensive academic note generation
    prompt = f"""
    Create a comprehensive educational note based on this lecture/course content.
    PRESERVE the teaching style, specific examples, and educational flow from the original transcript.
    
    CONTEXT:
    Title: {state["title"]} (Educational Content)
    Main Concepts: {", ".join(state["main_concepts"])}
    
    ORIGINAL TEACHING CONTENT (CORRECTED):
    {state["corrected_explanations"][:4000]}
    
    SUPPLEMENTARY RESEARCH:
    {detailed_research[:4000]}
    
    CRITICAL REQUIREMENTS:
    1. PRESERVE ALL specific examples mentioned by the instructor
    2. MAINTAIN the teaching narrative and progression
    3. KEEP the educational context - this is a lecture/course content, not a research paper
    4. ONLY add information that enhances understanding of what was taught
    5. PRESERVE instructor's voice and pedagogical approach
    
    STRUCTURE:
    
    # [Title] - Educational Notes
    
    ## Lecture Overview
    [Summary of what the instructor taught, maintaining educational context]
    
    ## Key Concepts Explained
    [Concepts as taught by instructor, with [[Obsidian links]] for navigation]
    
    ## Instructor Examples and Demonstrations
    [ALL specific examples mentioned in the lecture, preserved exactly]
    
    ## Technical Details Covered
    [Technical content as explained in the lecture, enhanced with research]
    
    ## Mathematical Concepts
    [Any formulas or mathematical concepts taught, with LaTeX notation]
    
    ## Resources and Tools Mentioned
    [Specific datasets, tools, software, or resources mentioned by instructor]
    
    ## Practical Applications Discussed
    [Applications as presented in the lecture]
    
    ## Enhanced Understanding
    [Additional context from research that helps understand the lecture content]
    
    ## Implementation Notes
    [Technical implementation details relevant to what was taught]
    
    ## Related Concepts for Further Study
    [[[Links]] to related topics for continued learning]
    
    ## References for Deep Dive
    
    ### Foundational Books
    {chr(10).join(f"- {book}" for book in books)}
    
    ### Online Resources
    {chr(10).join(f"- {resource}" for resource in online_resources)}
    
    ### Research Papers
    {chr(10).join(f"- {paper}" for paper in papers)}
    
    ### Recent Developments
    {chr(10).join(f"- {dev}" for dev in recent_developments)}
    
    ## Study Notes
    [Key takeaways and learning objectives from this lecture]
    
    ## Tags
    #{" #".join([concept.lower().replace(" ", "-") for concept in state["main_concepts"]])} #educational-notes #lecture-notes #course-content
    
    VALIDATION RULES:
    - Every specific example in the original must appear in the note
    - Maintain the instructor's teaching progression
    - Don't add metrics or data not mentioned in the original
    - Preserve the educational, not research, context
    - Keep the accessible, teaching tone
    
    Generate educational notes that capture what was actually taught, enhanced with research context.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000  # Increased for comprehensive content
        )
        
        final_note = response.choices[0].message.content.strip()
        
        # Extract Obsidian links for tracking
        obsidian_links = re.findall(r'\[\[([^\]]+)\]\]', final_note)
        
        state["final_note"] = final_note
        state["obsidian_links"] = list(set(obsidian_links))
        
        print(f"  Generated comprehensive note with {len(obsidian_links)} Obsidian links")
        
    except Exception as e:
        print(f"Error generating note: {sanitize_error_message(e)}")
        state["final_note"] = f"# {state['title']}\n\nError generating comprehensive academic note: {str(e)}"
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
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(transcript_path))[0]
        # Clean filename for better organization
        clean_name = re.sub(r'[^\w\s-]', '', base_name.lower())
        clean_name = re.sub(r'[\s]+', '-', clean_name)
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

def batch_process_transcripts(transcripts_dir: str = "transcripts", output_dir: str = "knowledge_base"):
    """Process all transcript files in a directory including subtitles"""
    # Test LLM connection before processing
    print("Testing connection to LLM service...")
    if not test_llm_connection():
        print("\n❌ Cannot proceed without LLM connection. Please check your configuration.")
        return
    print("✅ LLM connection successful!\n")
    
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
    for transcript_file in transcript_files:
        if processing_interrupted:
            print("\n\n🛑 Batch processing interrupted by user")
            break
            
        print(f"\n--- Processing ({processed_successfully + 1}/{len(transcript_files)}): {transcript_file} ---")
        result = process_transcript_to_academic_note(transcript_file, output_dir)
        if result:
            processed_successfully += 1
        else:
            print(f"Failed to process: {transcript_file}")
    
    print(f"\n=== Batch Processing {'Interrupted' if processing_interrupted else 'Complete'} ===")
    print(f"Successfully processed: {processed_successfully}/{len(transcript_files)} files")
    if processing_interrupted:
        print(f"Skipped: {len(transcript_files) - processed_successfully} files due to interruption")
    print(f"Academic notes saved in: {output_dir}/")

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch":
            batch_process_transcripts()
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