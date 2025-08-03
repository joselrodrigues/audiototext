#!/usr/bin/env python3
"""Enhanced pipeline integrating all agents for context-aware note generation"""

import os
import sys
import click
import asyncio
from pathlib import Path
from datetime import datetime

# Import existing agents
from agents import process_transcript_to_academic_note_async, batch_process_transcripts
from simple_vector_store import SimpleVectorStore
from context_agent import ContextAggregationAgent
from enhancement_agent import EnhancementAgent
from config import TRANSCRIPTS_FOLDER, KNOWLEDGE_BASE_FOLDER


class EnhancedPipeline:
    """Enhanced pipeline with context-aware processing"""
    
    def __init__(self):
        """Initialize the enhanced pipeline"""
        self.vector_store = SimpleVectorStore()
        self.context_agent = None
        self.enhancement_agent = None
        self.initialized = False
    
    def initialize(self):
        """Initialize all components"""
        print("🚀 Initializing enhanced pipeline...")
        
        # Connect to vector store
        if not self.vector_store.connect():
            print("❌ Failed to connect to vector store")
            return False
        
        # Initialize agents
        self.context_agent = ContextAggregationAgent(self.vector_store)
        self.enhancement_agent = EnhancementAgent(self.vector_store, self.context_agent)
        
        self.initialized = True
        print("✅ Enhanced pipeline initialized successfully")
        return True
    
    def index_existing_content(self, force_reindex: bool = False):
        """Index existing transcripts and knowledge base content"""
        print("📚 Indexing existing content...")
        
        if not self.initialized:
            print("❌ Pipeline not initialized")
            return False
        
        # Check if already indexed
        stats = self.vector_store.get_stats()
        if stats['transcripts'] > 0 or stats['knowledge_notes'] > 0:
            if not force_reindex:
                print(f"✅ Content already indexed ({stats['transcripts']} transcripts, {stats['knowledge_notes']} notes)")
                return True
            else:
                print("🔄 Force reindexing...")
                self.vector_store.delete_all()
        
        # Index transcripts
        transcript_count = 0
        if os.path.exists(TRANSCRIPTS_FOLDER):
            for root, _, files in os.walk(TRANSCRIPTS_FOLDER):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        chunks = self.vector_store.index_transcript(file_path)
                        if chunks > 0:
                            transcript_count += 1
        
        # Index knowledge base
        note_count = 0
        if os.path.exists(KNOWLEDGE_BASE_FOLDER):
            for root, _, files in os.walk(KNOWLEDGE_BASE_FOLDER):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        if self.vector_store.index_knowledge_note(file_path):
                            note_count += 1
        
        print(f"✅ Indexing complete: {transcript_count} transcripts, {note_count} notes")
        return True
    
    def generate_global_context(self, course_folder: str = None):
        """Generate global context for enhancement"""
        print("🌍 Generating global context...")
        
        if not self.initialized:
            print("❌ Pipeline not initialized")
            return None
        
        context = self.context_agent.generate_global_context(course_folder)
        
        # Save context for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        context_file = f"global_context_{timestamp}.json"
        self.context_agent.save_context(context, context_file)
        
        print(f"✅ Global context generated and saved to: {context_file}")
        return context
    
    def enhance_existing_notes(self, backup: bool = True, course_folder: str = None):
        """Enhance existing notes with global context"""
        print("🔧 Enhancing existing notes...")
        
        if not self.initialized:
            print("❌ Pipeline not initialized")
            return False
        
        # Generate global context
        global_context = self.generate_global_context(course_folder)
        if not global_context:
            print("❌ Failed to generate global context")
            return False
        
        # Enhance notes
        enhancement_results = self.enhancement_agent.enhance_notes_in_directory(
            KNOWLEDGE_BASE_FOLDER, 
            global_context, 
            backup=backup
        )
        
        if "error" in enhancement_results:
            print(f"❌ Enhancement failed: {enhancement_results['error']}")
            return False
        
        print(f"✅ Enhancement complete:")
        print(f"  Enhanced: {enhancement_results['enhanced']}/{enhancement_results['total_files']} files")
        print(f"  Success rate: {enhancement_results['summary']['success_rate']}")
        
        return True
    
    def process_new_content(self, input_folder: str = None):
        """Process new transcripts and generate enhanced notes"""
        print("🆕 Processing new content with enhanced pipeline...")
        
        if not self.initialized:
            print("❌ Pipeline not initialized")
            return False
        
        # Step 1: Run original batch processing
        print("Step 1: Running original transcript processing...")
        batch_process_transcripts()
        
        # Step 2: Index new content
        print("Step 2: Indexing new content...")
        self.index_existing_content()
        
        # Step 3: Generate global context
        print("Step 3: Generating global context...")
        global_context = self.generate_global_context()
        
        # Step 4: Enhance notes
        print("Step 4: Enhancing notes with context...")
        self.enhance_existing_notes(backup=True)
        
        print("✅ Enhanced processing complete!")
        return True


@click.group()
def cli():
    """Enhanced AudioToText Pipeline with Context Awareness"""
    pass


@cli.command()
@click.option('--force-reindex', is_flag=True, help='Force reindexing of existing content')
def index(force_reindex):
    """Index existing content into vector store"""
    pipeline = EnhancedPipeline()
    if pipeline.initialize():
        pipeline.index_existing_content(force_reindex)


@cli.command()
@click.option('--course', help='Generate context for specific course folder')
@click.option('--save-as', help='Save context to specific file')
def context(course, save_as):
    """Generate global context analysis"""
    pipeline = EnhancedPipeline()
    if pipeline.initialize():
        global_context = pipeline.generate_global_context(course)
        if save_as and global_context:
            pipeline.context_agent.save_context(global_context, save_as)
            print(f"Context saved to: {save_as}")


@cli.command()
@click.option('--no-backup', is_flag=True, help='Skip creating backups')
@click.option('--course', help='Enhance notes for specific course')
@click.option('--preview', help='Preview enhancement for specific file')
def enhance(no_backup, course, preview):
    """Enhance existing notes with global context"""
    pipeline = EnhancedPipeline()
    if not pipeline.initialize():
        return
    
    if preview:
        # Preview mode
        if not os.path.exists(preview):
            print(f"❌ File not found: {preview}")
            return
        
        global_context = pipeline.generate_global_context(course)
        if global_context:
            preview_content = pipeline.enhancement_agent.preview_enhancement(preview, global_context)
            
            # Save preview
            preview_file = f"preview_{os.path.basename(preview)}_{datetime.now().strftime('%H%M%S')}"
            with open(preview_file, 'w', encoding='utf-8') as f:
                f.write(preview_content)
            
            print(f"✅ Preview saved to: {preview_file}")
    else:
        # Full enhancement
        pipeline.enhance_existing_notes(backup=not no_backup, course_folder=course)


@cli.command()
def process():
    """Run complete enhanced processing pipeline"""
    pipeline = EnhancedPipeline()
    if pipeline.initialize():
        pipeline.process_new_content()


@cli.command()
def status():
    """Show pipeline status and statistics"""
    pipeline = EnhancedPipeline()
    if not pipeline.initialize():
        return
    
    print("📊 Enhanced Pipeline Status")
    print("=" * 40)
    
    # Vector store stats
    stats = pipeline.vector_store.get_stats()
    print(f"Vector Store:")
    print(f"  Transcripts indexed: {stats['transcripts']}")
    print(f"  Knowledge notes indexed: {stats['knowledge_notes']}")
    
    # File system stats
    transcript_files = []
    note_files = []
    
    if os.path.exists(TRANSCRIPTS_FOLDER):
        for root, _, files in os.walk(TRANSCRIPTS_FOLDER):
            transcript_files.extend([f for f in files if f.endswith('.md')])
    
    if os.path.exists(KNOWLEDGE_BASE_FOLDER):
        for root, _, files in os.walk(KNOWLEDGE_BASE_FOLDER):
            note_files.extend([f for f in files if f.endswith('.md')])
    
    print(f"\nFile System:")
    print(f"  Transcript files: {len(transcript_files)}")
    print(f"  Knowledge base files: {len(note_files)}")
    
    # Course detection
    course_folders = pipeline.context_agent.find_course_folders()
    print(f"\nCourses Detected:")
    for folder in course_folders:
        print(f"  - {folder}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if stats['transcripts'] == 0 and len(transcript_files) > 0:
        print("  - Run 'index' to index transcript files")
    if stats['knowledge_notes'] == 0 and len(note_files) > 0:
        print("  - Run 'index' to index knowledge base files")
    if len(note_files) > 0:
        print("  - Run 'enhance' to improve notes with context")
    if len(transcript_files) == 0:
        print("  - Run transcript processing first to generate content")


@cli.command()
@click.argument('query')
@click.option('--collection', default='transcripts', help='Collection to search (transcripts or knowledge_notes)')
@click.option('--limit', default=5, help='Number of results')
def search(query, collection, limit):
    """Search content in vector store"""
    pipeline = EnhancedPipeline()
    if not pipeline.initialize():
        return
    
    print(f"🔍 Searching for: '{query}' in {collection}")
    print("=" * 50)
    
    results = pipeline.vector_store.search(query, collection, limit)
    
    if not results:
        print("No results found.")
        return
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('lecture_name', 'Unknown')}")
        print(f"   Source: {os.path.basename(result.get('source_file', 'Unknown'))}")
        print(f"   Distance: {result.get('distance', 'N/A'):.3f}")
        print(f"   Content: {result.get('content', '')[:200]}...")


if __name__ == "__main__":
    cli()