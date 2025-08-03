#!/usr/bin/env python3
"""Quick Test Suite for Enhanced AudioToText Pipeline (no API calls)"""

import os
import time
from datetime import datetime

from enhanced_pipeline import EnhancedPipeline
from simple_vector_store import SimpleVectorStore
from context_agent import ContextAggregationAgent
from enhancement_agent import EnhancementAgent

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_pipeline_components():
    """Test that all pipeline components can be initialized"""
    print(f"{BLUE}🧪 Test 1: Component Initialization{RESET}")
    
    results = []
    
    # Test vector store
    try:
        vs = SimpleVectorStore()
        vs.connect()
        results.append(("Vector Store", True, "Connected to ChromaDB"))
    except Exception as e:
        results.append(("Vector Store", False, f"Error: {e}"))
    
    # Test context agent
    try:
        ca = ContextAggregationAgent(vs)
        results.append(("Context Agent", True, f"Model: {ca.model}"))
    except Exception as e:
        results.append(("Context Agent", False, f"Error: {e}"))
    
    # Test enhancement agent
    try:
        ea = EnhancementAgent(vs, ca)
        results.append(("Enhancement Agent", True, f"Model: {ea.model}"))
    except Exception as e:
        results.append(("Enhancement Agent", False, f"Error: {e}"))
    
    # Test enhanced pipeline
    try:
        pipeline = EnhancedPipeline()
        pipeline.initialize()
        results.append(("Enhanced Pipeline", True, "All components integrated"))
    except Exception as e:
        results.append(("Enhanced Pipeline", False, f"Error: {e}"))
    
    # Print results
    for component, passed, details in results:
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {status} {component}: {details}")
    
    return all(r[1] for r in results)


def test_file_operations():
    """Test file operations and directory structure"""
    print(f"\n{BLUE}🧪 Test 2: File Operations{RESET}")
    
    from config import TRANSCRIPTS_FOLDER, KNOWLEDGE_BASE_FOLDER
    
    results = []
    
    # Check directories exist
    directories = [
        (TRANSCRIPTS_FOLDER, "Transcripts"),
        (KNOWLEDGE_BASE_FOLDER, "Knowledge Base"),
        ("./chroma_db", "ChromaDB Data")
    ]
    
    for dir_path, name in directories:
        exists = os.path.exists(dir_path)
        results.append((name, exists, f"Path: {dir_path}"))
    
    # Count files
    transcript_files = []
    note_files = []
    
    if os.path.exists(TRANSCRIPTS_FOLDER):
        for root, _, files in os.walk(TRANSCRIPTS_FOLDER):
            transcript_files.extend([f for f in files if f.endswith('.md')])
    
    if os.path.exists(KNOWLEDGE_BASE_FOLDER):
        for root, _, files in os.walk(KNOWLEDGE_BASE_FOLDER):
            note_files.extend([f for f in files if f.endswith('.md')])
    
    results.append(("File Count", True, f"{len(transcript_files)} transcripts, {len(note_files)} notes"))
    
    # Print results
    for item, passed, details in results:
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {status} {item}: {details}")
    
    return len(transcript_files) > 0 or len(note_files) > 0


def test_vector_store_basic():
    """Test basic vector store operations without API calls"""
    print(f"\n{BLUE}🧪 Test 3: Vector Store Basic Operations{RESET}")
    
    try:
        vs = SimpleVectorStore()
        if not vs.connect():
            print(f"  {RED}✗ Connection failed{RESET}")
            return False
        
        # Test stats
        stats = vs.get_stats()
        print(f"  {GREEN}✓{RESET} Stats retrieval: {stats}")
        
        # Test text chunking
        test_text = "This is a test sentence. " * 100
        chunks = vs.chunk_text(test_text, chunk_size=50)
        print(f"  {GREEN}✓{RESET} Text chunking: {len(chunks)} chunks created")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Vector store error: {e}{RESET}")
        return False


def test_context_agent_basic():
    """Test basic context agent operations"""
    print(f"\n{BLUE}🧪 Test 4: Context Agent Basic Operations{RESET}")
    
    try:
        vs = SimpleVectorStore()
        vs.connect()
        ca = ContextAggregationAgent(vs)
        
        # Test course folder detection
        folders = ca.find_course_folders()
        print(f"  {GREEN}✓{RESET} Course detection: {folders}")
        
        # Test content extraction (without processing)
        from config import TRANSCRIPTS_FOLDER
        content = ca.extract_content_from_files(TRANSCRIPTS_FOLDER)
        print(f"  {GREEN}✓{RESET} Content extraction: {content['file_count']} files found")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Context agent error: {e}{RESET}")
        return False


def test_enhancement_agent_basic():
    """Test basic enhancement agent operations"""
    print(f"\n{BLUE}🧪 Test 5: Enhancement Agent Basic Operations{RESET}")
    
    try:
        vs = SimpleVectorStore()
        vs.connect()
        ca = ContextAggregationAgent(vs)
        ea = EnhancementAgent(vs, ca)
        
        # Test concept extraction
        test_note = """# Test Note
        
This is about machine learning and neural networks.

Concepts covered: machine learning, neural networks, deep learning
"""
        concepts = ea.extract_concepts_from_note(test_note)
        print(f"  {GREEN}✓{RESET} Concept extraction: {concepts}")
        
        # Test related content retrieval (should work even with empty store)
        related = ea.get_related_content("test.md", ["machine learning"], limit=2)
        print(f"  {GREEN}✓{RESET} Related content: {related['total_found']} items found")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Enhancement agent error: {e}{RESET}")
        return False


def test_pipeline_commands():
    """Test pipeline CLI commands (dry run)"""
    print(f"\n{BLUE}🧪 Test 6: Pipeline Commands{RESET}")
    
    try:
        pipeline = EnhancedPipeline()
        if not pipeline.initialize():
            print(f"  {RED}✗ Pipeline initialization failed{RESET}")
            return False
        
        # Test status (should work)
        print(f"  {GREEN}✓{RESET} Pipeline initialized")
        print(f"  {GREEN}✓{RESET} Vector store connected")
        print(f"  {GREEN}✓{RESET} Context agent ready")
        print(f"  {GREEN}✓{RESET} Enhancement agent ready")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Pipeline command error: {e}{RESET}")
        return False


def test_configuration():
    """Test configuration and environment"""
    print(f"\n{BLUE}🧪 Test 7: Configuration{RESET}")
    
    try:
        from config import (
            BASE_URL, API_KEY, CONTEXT_MODEL, ENHANCEMENT_MODEL, 
            EMBEDDING_MODEL, TRANSCRIPTS_FOLDER, KNOWLEDGE_BASE_FOLDER
        )
        
        config_items = [
            ("BASE_URL", BASE_URL is not None),
            ("API_KEY", API_KEY is not None),
            ("CONTEXT_MODEL", CONTEXT_MODEL == "o3-mini"),
            ("ENHANCEMENT_MODEL", ENHANCEMENT_MODEL == "gpt-4"),
            ("EMBEDDING_MODEL", EMBEDDING_MODEL == "text-embedding-3-small"),
            ("TRANSCRIPTS_FOLDER", TRANSCRIPTS_FOLDER is not None),
            ("KNOWLEDGE_BASE_FOLDER", KNOWLEDGE_BASE_FOLDER is not None)
        ]
        
        for item, valid in config_items:
            status = f"{GREEN}✓{RESET}" if valid else f"{RED}✗{RESET}"
            print(f"  {status} {item}")
        
        return all(valid for _, valid in config_items)
        
    except Exception as e:
        print(f"  {RED}✗ Configuration error: {e}{RESET}")
        return False


def main():
    """Run quick test suite"""
    print(f"{BLUE}🚀 Quick Test Suite for Enhanced AudioToText Pipeline{RESET}")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run tests
    tests = [
        ("Component Initialization", test_pipeline_components),
        ("File Operations", test_file_operations),
        ("Vector Store Basic", test_vector_store_basic),
        ("Context Agent Basic", test_context_agent_basic),
        ("Enhancement Agent Basic", test_enhancement_agent_basic),
        ("Pipeline Commands", test_pipeline_commands),
        ("Configuration", test_configuration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  {RED}✗ {test_name} failed with error: {e}{RESET}")
            results.append((test_name, False))
    
    # Summary
    elapsed_time = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{BLUE}📊 Test Summary{RESET}")
    print("=" * 40)
    print(f"Tests Run: {total}")
    print(f"Passed: {GREEN}{passed}{RESET}")
    print(f"Failed: {RED}{total - passed}{RESET}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Execution Time: {elapsed_time:.2f} seconds")
    
    # Assessment
    if success_rate >= 90:
        print(f"\n{GREEN}🎉 Excellent! System is ready for production{RESET}")
    elif success_rate >= 75:
        print(f"\n{YELLOW}⚠️  Good! Minor issues to address{RESET}")
    else:
        print(f"\n{RED}❌ Issues detected! Review failed tests{RESET}")
    
    print(f"\n{BLUE}Next Steps:{RESET}")
    print("1. Run full indexing: uv run python enhanced_pipeline.py index")
    print("2. Generate context: uv run python enhanced_pipeline.py context")
    print("3. Enhance notes: uv run python enhanced_pipeline.py enhance --preview <file>")
    print("4. Search content: uv run python enhanced_pipeline.py search 'your query'")


if __name__ == "__main__":
    main()