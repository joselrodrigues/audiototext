#!/usr/bin/env python3
"""Context Aggregation Agent for analyzing course-wide context using o3-mini"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from openai import OpenAI

from config import (
    BASE_URL, 
    API_KEY, 
    CONTEXT_MODEL,
    TRANSCRIPTS_FOLDER,
    KNOWLEDGE_BASE_FOLDER
)
from simple_vector_store import SimpleVectorStore


class ContextAggregationAgent:
    """Analyzes course content to generate global context using o3-mini"""
    
    def __init__(self, vector_store: Optional[SimpleVectorStore] = None):
        """Initialize the context agent"""
        self.client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        self.model = CONTEXT_MODEL
        self.vector_store = vector_store
        
        # Initialize vector store if not provided
        if not self.vector_store:
            self.vector_store = SimpleVectorStore()
            self.vector_store.connect()
    
    def find_course_folders(self) -> List[str]:
        """Find all course folders in transcripts directory"""
        course_folders = set()
        
        # Check transcripts folder
        if os.path.exists(TRANSCRIPTS_FOLDER):
            for root, dirs, files in os.walk(TRANSCRIPTS_FOLDER):
                for file in files:
                    if file.endswith('.md'):
                        # Get the folder containing this file
                        rel_path = os.path.relpath(root, TRANSCRIPTS_FOLDER)
                        if rel_path != '.':
                            course_folders.add(rel_path)
        
        # Check knowledge base folder
        if os.path.exists(KNOWLEDGE_BASE_FOLDER):
            for root, dirs, files in os.walk(KNOWLEDGE_BASE_FOLDER):
                for file in files:
                    if file.endswith('.md'):
                        # Try to match with transcript structure
                        rel_path = os.path.relpath(root, KNOWLEDGE_BASE_FOLDER)
                        if rel_path != '.':
                            course_folders.add(rel_path)
        
        return sorted(list(course_folders)) if course_folders else ["general"]
    
    def extract_content_from_files(self, directory: str, course_folder: str = "") -> Dict[str, Any]:
        """Extract content from files in a directory"""
        content = {
            "files": [],
            "total_content": "",
            "file_count": 0
        }
        
        if not os.path.exists(directory):
            return content
        
        search_dir = os.path.join(directory, course_folder) if course_folder else directory
        if not os.path.exists(search_dir):
            search_dir = directory
        
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        # Remove YAML front matter
                        if file_content.startswith('---'):
                            parts = file_content.split('---', 2)
                            if len(parts) > 2:
                                file_content = parts[2].strip()
                        
                        content["files"].append({
                            "name": file,
                            "path": file_path,
                            "content": file_content[:2000],  # Limit content length
                            "length": len(file_content)
                        })
                        content["total_content"] += f"\n\n=== {file} ===\n{file_content[:1000]}"
                        content["file_count"] += 1
                        
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
        
        return content
    
    def analyze_course_structure(self, course_folder: str = "general") -> Dict[str, Any]:
        """Analyze the structure and content of a course"""
        print(f"📚 Analyzing course structure for: {course_folder}")
        
        # Extract content from transcripts and knowledge base
        transcripts = self.extract_content_from_files(TRANSCRIPTS_FOLDER, course_folder)
        knowledge_notes = self.extract_content_from_files(KNOWLEDGE_BASE_FOLDER, course_folder)
        
        # Get vector store context if available
        vector_context = {}
        try:
            vector_context = self.vector_store.get_course_context(course_folder)
        except Exception as e:
            print(f"Warning: Could not get vector context: {e}")
        
        total_files = transcripts["file_count"] + knowledge_notes["file_count"]
        if total_files == 0:
            print(f"❌ No files found for course: {course_folder}")
            return {"error": "No files found"}
        
        print(f"  Found {transcripts['file_count']} transcripts and {knowledge_notes['file_count']} notes")
        
        # Prepare prompt for o3-mini
        analysis_prompt = f"""
        Analyze this educational course content and extract key structural information.
        
        Course Folder: {course_folder}
        Transcript Files: {transcripts['file_count']}
        Knowledge Notes: {knowledge_notes['file_count']}
        
        TRANSCRIPT CONTENT:
        {transcripts['total_content'][:3000]}
        
        KNOWLEDGE NOTES CONTENT:
        {knowledge_notes['total_content'][:3000]}
        
        Provide a comprehensive analysis in the following JSON format:
        {{
            "course_name": "Human-readable course name",
            "course_description": "Brief description of what this course covers",
            "main_topics": ["topic1", "topic2", "topic3"],
            "lecture_sequence": [
                {{"lecture": "lecture1", "title": "Title", "main_concepts": ["concept1", "concept2"]}},
                {{"lecture": "lecture2", "title": "Title", "main_concepts": ["concept1", "concept2"]}}
            ],
            "concept_progression": {{
                "prerequisites": {{"advanced_concept": ["basic_concept1", "basic_concept2"]}},
                "learning_path": ["start_here", "then_this", "finally_this"]
            }},
            "key_vocabulary": ["term1", "term2", "term3"],
            "difficulty_level": "beginner|intermediate|advanced",
            "estimated_duration": "X hours",
            "learning_objectives": ["objective1", "objective2"],
            "course_themes": ["theme1", "theme2"]
        }}
        
        Focus on educational structure, concept relationships, and learning progression.
        Be accurate and base your analysis only on the provided content.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, extract key information
                analysis = {
                    "course_name": course_folder.replace('-', ' ').title(),
                    "course_description": "Auto-generated course analysis",
                    "main_topics": [],
                    "raw_analysis": analysis_text
                }
            
            # Add metadata
            analysis["metadata"] = {
                "course_folder": course_folder,
                "transcript_files": [f["name"] for f in transcripts["files"]],
                "knowledge_files": [f["name"] for f in knowledge_notes["files"]],
                "total_files": total_files,
                "analysis_date": datetime.now().isoformat(),
                "model_used": self.model,
                "vector_stats": {
                    "transcript_chunks": vector_context.get("transcript_count", 0),
                    "note_chunks": vector_context.get("note_count", 0)
                }
            }
            
            print(f"✅ Course analysis completed for {course_folder}")
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing course structure: {e}")
            return {"error": str(e)}
    
    def identify_cross_course_relationships(self, course_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify relationships between multiple courses"""
        if len(course_analyses) <= 1:
            return {"relationships": "Single course - no cross-relationships"}
        
        print("🔗 Analyzing cross-course relationships...")
        
        # Prepare content for analysis
        courses_summary = []
        for analysis in course_analyses:
            if "error" not in analysis:
                courses_summary.append({
                    "name": analysis.get("course_name", "Unknown"),
                    "topics": analysis.get("main_topics", []),
                    "vocabulary": analysis.get("key_vocabulary", []),
                    "level": analysis.get("difficulty_level", "unknown")
                })
        
        relationship_prompt = f"""
        Analyze relationships between these educational courses:
        
        {json.dumps(courses_summary, indent=2)}
        
        Provide analysis in JSON format:
        {{
            "prerequisite_relationships": [
                {{"prerequisite": "Course A", "enables": "Course B", "reason": "explanation"}}
            ],
            "shared_concepts": [
                {{"concept": "neural networks", "courses": ["Course A", "Course B"], "progression": "how it evolves"}}
            ],
            "learning_sequence": ["Course 1", "Course 2", "Course 3"],
            "complementary_topics": [
                {{"courses": ["A", "B"], "how_they_complement": "explanation"}}
            ],
            "difficulty_progression": {{"beginner": ["Course A"], "intermediate": ["Course B"], "advanced": ["Course C"]}},
            "recommended_study_paths": [
                {{"path_name": "Foundation Track", "sequence": ["Course A", "Course B"]}}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": relationship_prompt}],
                max_tokens=1500,
                temperature=0.1
            )
            
            relationship_text = response.choices[0].message.content.strip()
            
            try:
                relationships = json.loads(relationship_text)
            except json.JSONDecodeError:
                relationships = {"raw_analysis": relationship_text}
            
            relationships["metadata"] = {
                "courses_analyzed": len(courses_summary),
                "analysis_date": datetime.now().isoformat()
            }
            
            print(f"✅ Cross-course relationship analysis completed")
            return relationships
            
        except Exception as e:
            print(f"❌ Error analyzing cross-course relationships: {e}")
            return {"error": str(e)}
    
    def generate_global_context(self, course_folder: str = None) -> Dict[str, Any]:
        """Generate comprehensive global context for all courses or specific course"""
        print("🌍 Generating global context...")
        
        if course_folder:
            # Single course analysis
            course_analyses = [self.analyze_course_structure(course_folder)]
            cross_relationships = {"single_course": True}
        else:
            # Multi-course analysis
            course_folders = self.find_course_folders()
            print(f"Found {len(course_folders)} course folders: {course_folders}")
            
            course_analyses = []
            for folder in course_folders:
                analysis = self.analyze_course_structure(folder)
                if "error" not in analysis:
                    course_analyses.append(analysis)
            
            cross_relationships = self.identify_cross_course_relationships(course_analyses)
        
        # Generate global context
        global_context = {
            "context_type": "global" if not course_folder else "single_course",
            "target_course": course_folder,
            "generated_at": datetime.now().isoformat(),
            "model_used": self.model,
            "courses": {
                analysis.get("course_name", "Unknown"): analysis 
                for analysis in course_analyses if "error" not in analysis
            },
            "cross_course_relationships": cross_relationships,
            "summary": {
                "total_courses": len(course_analyses),
                "total_files": sum(
                    analysis.get("metadata", {}).get("total_files", 0) 
                    for analysis in course_analyses if "error" not in analysis
                ),
                "main_domains": list(set(
                    topic for analysis in course_analyses if "error" not in analysis
                    for topic in analysis.get("main_topics", [])
                ))
            }
        }
        
        print(f"✅ Global context generated successfully")
        print(f"  Courses analyzed: {len(course_analyses)}")
        print(f"  Total files: {global_context['summary']['total_files']}")
        
        return global_context
    
    def save_context(self, context: Dict[str, Any], output_path: str = None) -> str:
        """Save context to file"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if context.get("target_course"):
                output_path = f"context_{context['target_course']}_{timestamp}.json"
            else:
                output_path = f"global_context_{timestamp}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Context saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error saving context: {e}")
            return ""


def main():
    """Test the context aggregation agent"""
    agent = ContextAggregationAgent()
    
    # Generate global context
    context = agent.generate_global_context()
    
    # Save context
    output_file = agent.save_context(context)
    
    print(f"\n📊 Context Analysis Summary:")
    print(f"  Courses found: {len(context['courses'])}")
    print(f"  Total files: {context['summary']['total_files']}")
    print(f"  Main domains: {', '.join(context['summary']['main_domains'][:5])}")
    print(f"  Output file: {output_file}")


if __name__ == "__main__":
    main()