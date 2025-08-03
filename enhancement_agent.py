#!/usr/bin/env python3
"""Enhancement Agent for improving notes with global context using GPT-4"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from openai import OpenAI

from config import (
    BASE_URL, 
    API_KEY, 
    CONTEXT_MODEL,  # Use o3-mini instead of gpt-4
    TRANSCRIPTS_FOLDER,
    KNOWLEDGE_BASE_FOLDER
)
from simple_vector_store import SimpleVectorStore
from context_agent import ContextAggregationAgent


class EnhancementAgent:
    """Enhances existing notes with global context and validation using o3-mini"""
    
    def __init__(self, vector_store: Optional[SimpleVectorStore] = None, context_agent: Optional[ContextAggregationAgent] = None):
        """Initialize the enhancement agent"""
        self.client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        self.model = CONTEXT_MODEL  # Use o3-mini for enhancement
        
        # Initialize vector store if not provided
        if not vector_store:
            self.vector_store = SimpleVectorStore()
            self.vector_store.connect()
        else:
            self.vector_store = vector_store
        
        # Initialize context agent if not provided
        if not context_agent:
            self.context_agent = ContextAggregationAgent(self.vector_store)
        else:
            self.context_agent = context_agent
    
    def load_original_transcript(self, note_file: str) -> str:
        """Find and load the original transcript for a knowledge note"""
        # Extract the base name without extensions
        note_name = Path(note_file).stem
        
        # Remove common suffixes to match with transcript
        clean_name = note_name.replace('-subtitles', '').replace('_subtitles', '')
        
        # Search for matching transcript
        transcript_candidates = []
        
        if os.path.exists(TRANSCRIPTS_FOLDER):
            for root, _, files in os.walk(TRANSCRIPTS_FOLDER):
                for file in files:
                    if file.endswith('.md'):
                        file_stem = Path(file).stem
                        clean_file = file_stem.replace('-subtitles', '').replace('_subtitles', '')
                        
                        if clean_file == clean_name or clean_name in clean_file:
                            transcript_candidates.append(os.path.join(root, file))
        
        # Return the first match or empty string
        if transcript_candidates:
            try:
                with open(transcript_candidates[0], 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove YAML front matter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) > 2:
                            content = parts[2].strip()
                    return content
            except Exception as e:
                print(f"Warning: Could not read transcript {transcript_candidates[0]}: {e}")
        
        return ""
    
    def get_related_content(self, note_file: str, concepts: List[str], limit: int = 5) -> Dict[str, Any]:
        """Get related content from vector store based on concepts"""
        related_content = {
            "transcripts": [],
            "notes": [],
            "total_found": 0
        }
        
        try:
            # Search for related content for each concept
            all_results = []
            
            for concept in concepts[:5]:  # Limit to top 5 concepts
                # Search transcripts
                transcript_results = self.vector_store.search(
                    query=concept, 
                    collection="transcripts", 
                    limit=3
                )
                
                # Search notes
                note_results = self.vector_store.search(
                    query=concept,
                    collection="knowledge_notes",
                    limit=2
                )
                
                for result in transcript_results:
                    if result.get('source_file') != note_file:  # Exclude self
                        all_results.append(("transcript", result))
                
                for result in note_results:
                    if result.get('source_file') != note_file:  # Exclude self
                        all_results.append(("note", result))
            
            # Deduplicate and organize results
            seen_sources = set()
            for content_type, result in all_results:
                source = result.get('source_file', '')
                if source and source not in seen_sources:
                    seen_sources.add(source)
                    
                    if content_type == "transcript":
                        related_content["transcripts"].append({
                            "source": source,
                            "lecture_name": result.get('lecture_name', ''),
                            "content_preview": result.get('content', '')[:300] + "...",
                            "relevance": result.get('distance', 1.0)
                        })
                    else:
                        related_content["notes"].append({
                            "source": source,
                            "title": result.get('title', ''),
                            "content_preview": result.get('content', '')[:300] + "...",
                            "relevance": result.get('distance', 1.0)
                        })
            
            related_content["total_found"] = len(seen_sources)
            
        except Exception as e:
            print(f"Warning: Could not get related content: {e}")
        
        return related_content
    
    def extract_concepts_from_note(self, note_content: str) -> List[str]:
        """Extract main concepts from a note"""
        concepts = []
        
        # Look for explicit concept mentions
        if "Concepts covered:" in note_content:
            for line in note_content.split('\n'):
                if line.startswith('Concepts covered:'):
                    concepts_text = line.replace('Concepts covered:', '').strip()
                    concepts = [c.strip() for c in concepts_text.split(',')]
                    break
        
        # If no explicit concepts, extract from title and headers
        if not concepts:
            lines = note_content.split('\n')
            for line in lines:
                if line.startswith('# ') or line.startswith('## '):
                    title = line.lstrip('#').strip()
                    # Simple keyword extraction
                    words = title.lower().split()
                    if len(words) <= 4:  # Short phrases likely to be concepts
                        concepts.append(title)
        
        return concepts[:10]  # Limit to 10 concepts
    
    def enhance_note_with_context(self, note_file: str, global_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a single note with global context and validation"""
        print(f"🔧 Enhancing note: {os.path.basename(note_file)}")
        
        try:
            # Read the current note
            with open(note_file, 'r', encoding='utf-8') as f:
                current_note = f.read()
            
            # Extract concepts from current note
            concepts = self.extract_concepts_from_note(current_note)
            
            # Load original transcript
            original_transcript = self.load_original_transcript(note_file)
            
            # Get related content from vector store
            related_content = self.get_related_content(note_file, concepts)
            
            # Get course-specific context
            note_path = Path(note_file)
            course_folder = note_path.parent.name if note_path.parent.name != KNOWLEDGE_BASE_FOLDER else "general"
            course_context = global_context.get("courses", {}).get(course_folder, {})
            
            # Prepare enhancement prompt
            enhancement_prompt = f"""
You are an expert educational content enhancer. Your task is to improve an existing academic note by:

1. Adding relevant context from the course
2. Cross-referencing with related materials
3. Validating against the original transcript
4. Maintaining the educational voice and structure

CURRENT NOTE TO ENHANCE:
{current_note[:4000]}

ORIGINAL TRANSCRIPT (for validation):
{original_transcript[:3000] if original_transcript else "No original transcript available"}

COURSE CONTEXT:
Course: {course_context.get('course_name', 'Unknown')}
Description: {course_context.get('course_description', 'No description')}
Main Topics: {', '.join(course_context.get('main_topics', []))}
Learning Path: {' → '.join(course_context.get('concept_progression', {}).get('learning_path', []))}

RELATED CONTENT FROM OTHER LECTURES:
Transcripts: {len(related_content['transcripts'])} related lectures found
Notes: {len(related_content['notes'])} related notes found

Sample related content:
{json.dumps(related_content['transcripts'][:2], indent=2) if related_content['transcripts'] else "No related transcripts"}

ENHANCEMENT INSTRUCTIONS:
1. **Preserve Original Structure**: Keep the existing markdown structure and main content
2. **Add Course Context Section**: Add a new section explaining how this fits in the overall course
3. **Cross-Reference Related Topics**: Add connections to other lectures/concepts
4. **Validate Facts**: Check against original transcript and correct any errors
5. **Enhance Explanations**: Expand explanations while maintaining the instructor's teaching style
6. **Add Learning Connections**: Show prerequisites and next steps in learning
7. **Maintain Academic Tone**: Keep it educational and well-structured

OUTPUT FORMAT:
Return the enhanced note in proper markdown format. Include:
- Original content (improved and validated)
- New "## Course Context" section
- New "## Related Topics" section  
- Enhanced "## References" section
- Improved concept explanations

Focus on adding value without changing the core educational message.
"""
            
            # Call o3-mini for enhancement
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": enhancement_prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            
            enhanced_content = response.choices[0].message.content.strip()
            
            # Add metadata section
            metadata_section = f"""

---
*Enhanced on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} using {self.model}*
*Original concepts: {', '.join(concepts[:5])}*
*Related materials: {related_content['total_found']} items*
"""
            
            enhanced_content += metadata_section
            
            print(f"✅ Note enhanced successfully")
            
            return {
                "status": "success",
                "original_length": len(current_note),
                "enhanced_length": len(enhanced_content),
                "concepts_found": len(concepts),
                "related_content_found": related_content['total_found'],
                "enhanced_content": enhanced_content,
                "original_transcript_available": bool(original_transcript),
                "course_context_available": bool(course_context)
            }
            
        except Exception as e:
            print(f"❌ Error enhancing note: {e}")
            return {
                "status": "error",
                "error": str(e),
                "enhanced_content": None
            }
    
    def enhance_notes_in_directory(self, directory: str, global_context: Dict[str, Any], backup: bool = True) -> Dict[str, Any]:
        """Enhance all notes in a directory"""
        print(f"📚 Enhancing notes in: {directory}")
        
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}
        
        # Find all markdown files
        note_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.md'):
                    note_files.append(os.path.join(root, file))
        
        if not note_files:
            return {"error": "No markdown files found"}
        
        print(f"Found {len(note_files)} notes to enhance")
        
        results = {
            "total_files": len(note_files),
            "enhanced": 0,
            "failed": 0,
            "skipped": 0,
            "files": {},
            "summary": {}
        }
        
        for i, note_file in enumerate(note_files, 1):
            print(f"\n[{i}/{len(note_files)}] Processing: {os.path.basename(note_file)}")
            
            try:
                # Create backup if requested
                if backup:
                    backup_file = note_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    with open(note_file, 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                
                # Enhance the note
                enhancement_result = self.enhance_note_with_context(note_file, global_context)
                
                if enhancement_result["status"] == "success":
                    # Write enhanced content
                    with open(note_file, 'w', encoding='utf-8') as f:
                        f.write(enhancement_result["enhanced_content"])
                    
                    results["enhanced"] += 1
                    results["files"][note_file] = {
                        "status": "enhanced",
                        "original_length": enhancement_result["original_length"],
                        "enhanced_length": enhancement_result["enhanced_length"],
                        "backup_created": backup
                    }
                else:
                    results["failed"] += 1
                    results["files"][note_file] = {
                        "status": "failed",
                        "error": enhancement_result.get("error", "Unknown error")
                    }
                
            except Exception as e:
                print(f"❌ Error processing {note_file}: {e}")
                results["failed"] += 1
                results["files"][note_file] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Generate summary
        results["summary"] = {
            "success_rate": f"{(results['enhanced'] / results['total_files'] * 100):.1f}%",
            "total_enhanced": results["enhanced"],
            "total_failed": results["failed"],
            "average_length_increase": 0
        }
        
        # Calculate average length increase
        length_increases = [
            r["enhanced_length"] - r["original_length"] 
            for r in results["files"].values() 
            if r["status"] == "enhanced" and "enhanced_length" in r
        ]
        
        if length_increases:
            results["summary"]["average_length_increase"] = sum(length_increases) // len(length_increases)
        
        print(f"\n✅ Enhancement complete!")
        print(f"  Enhanced: {results['enhanced']}/{results['total_files']}")
        print(f"  Success rate: {results['summary']['success_rate']}")
        
        return results
    
    def preview_enhancement(self, note_file: str, global_context: Dict[str, Any]) -> str:
        """Preview what enhancement would look like without saving"""
        enhancement_result = self.enhance_note_with_context(note_file, global_context)
        
        if enhancement_result["status"] == "success":
            return enhancement_result["enhanced_content"]
        else:
            return f"Enhancement failed: {enhancement_result.get('error', 'Unknown error')}"


def main():
    """Test the enhancement agent"""
    print("🔧 Testing Enhancement Agent")
    
    # Initialize agents
    vector_store = SimpleVectorStore()
    vector_store.connect()
    
    context_agent = ContextAggregationAgent(vector_store)
    enhancement_agent = EnhancementAgent(vector_store, context_agent)
    
    # Generate global context
    print("📊 Generating global context...")
    global_context = context_agent.generate_global_context()
    
    # Find a test note
    test_files = []
    if os.path.exists(KNOWLEDGE_BASE_FOLDER):
        for root, _, files in os.walk(KNOWLEDGE_BASE_FOLDER):
            for file in files:
                if file.endswith('.md'):
                    test_files.append(os.path.join(root, file))
    
    if test_files:
        test_file = test_files[0]
        print(f"🧪 Testing enhancement on: {os.path.basename(test_file)}")
        
        # Preview enhancement
        preview = enhancement_agent.preview_enhancement(test_file, global_context)
        print(f"✅ Preview generated ({len(preview)} characters)")
        
        # Save preview
        preview_file = f"enhancement_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write(preview)
        print(f"📄 Preview saved to: {preview_file}")
    else:
        print("❌ No test files found")


if __name__ == "__main__":
    main()