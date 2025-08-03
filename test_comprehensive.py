#!/usr/bin/env python3
"""Comprehensive Test Suite for Enhanced AudioToText Pipeline"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time

# Import all components
from enhanced_pipeline import EnhancedPipeline
from simple_vector_store import SimpleVectorStore
from context_agent import ContextAggregationAgent
from enhancement_agent import EnhancementAgent
from config import TRANSCRIPTS_FOLDER, KNOWLEDGE_BASE_FOLDER

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class ComprehensiveTestSuite:
    """Complete test suite for the enhanced pipeline"""
    
    def __init__(self):
        self.test_results = []
        self.pipeline = None
        self.test_data_created = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {test_name}: {status}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        return passed
    
    def create_test_data(self):
        """Create test data for comprehensive testing"""
        print(f"\n{BLUE}🏗️  Setting up test environment...{RESET}")
        
        # Create test directories
        test_dirs = [
            "test_transcripts/test-course",
            "test_knowledge/test-course"
        ]
        
        for test_dir in test_dirs:
            os.makedirs(test_dir, exist_ok=True)
            self.test_data_created.append(test_dir)
        
        # Create test transcript
        test_transcript = """---
title: Introduction to Neural Networks
date: 2025-01-01
course: Test Course
---

# Introduction to Neural Networks

This lecture introduces the fundamental concepts of neural networks and their applications in machine learning.

## What are Neural Networks?

Neural networks are computational models inspired by biological neural networks. They consist of interconnected nodes called neurons that process information.

## Key Components

### Neurons
Each neuron receives inputs, processes them using an activation function, and produces an output.

### Weights and Biases
Weights determine the strength of connections between neurons, while biases allow for adjusting the output.

### Activation Functions
Common activation functions include:
- Sigmoid
- ReLU (Rectified Linear Unit)
- Tanh

## Applications

Neural networks are used in:
- Image recognition
- Natural language processing
- Speech recognition
- Game playing (like AlphaGo)

## Training Process

The training process involves:
1. Forward propagation
2. Error calculation
3. Backpropagation
4. Weight updates

This process is repeated until the network achieves satisfactory performance.

## Conclusion

Neural networks form the foundation of modern deep learning systems and have revolutionized artificial intelligence.
"""
        
        # Create test knowledge base note
        test_note = """# Neural Network Fundamentals

## Overview
Neural networks are the building blocks of deep learning systems.

## Core Concepts
- Artificial neurons
- Activation functions
- Training algorithms

## Mathematical Foundation
Neural networks use matrix operations and calculus for optimization.

Concepts covered: neural networks, deep learning, machine learning, artificial intelligence

## References
1. Deep Learning by Ian Goodfellow
2. Neural Networks and Deep Learning by Michael Nielsen
3. Pattern Recognition and Machine Learning by Christopher Bishop
"""
        
        # Write test files
        transcript_path = "test_transcripts/test-course/neural-networks.md"
        note_path = "test_knowledge/test-course/neural-networks.md"
        
        with open(transcript_path, 'w') as f:
            f.write(test_transcript)
        self.test_data_created.append(transcript_path)
        
        with open(note_path, 'w') as f:
            f.write(test_note)
        self.test_data_created.append(note_path)
        
        return self.log_test("Test Data Creation", True, f"Created {len(self.test_data_created)} test items")
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print(f"\n{BLUE}🧹 Cleaning up test environment...{RESET}")
        
        for item in self.test_data_created:
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                elif os.path.isfile(item):
                    os.unlink(item)
            except Exception as e:
                print(f"Warning: Could not remove {item}: {e}")
        
        print(f"  Cleaned up {len(self.test_data_created)} items")
    
    def test_pipeline_initialization(self):
        """Test 1: Pipeline initialization"""
        print(f"\n{BLUE}🧪 Test 1: Pipeline Initialization{RESET}")
        
        try:
            self.pipeline = EnhancedPipeline()
            init_success = self.pipeline.initialize()
            
            if init_success and self.pipeline.initialized:
                return self.log_test("Pipeline Initialization", True, "All components initialized")
            else:
                return self.log_test("Pipeline Initialization", False, "Initialization failed")
                
        except Exception as e:
            return self.log_test("Pipeline Initialization", False, f"Error: {e}")
    
    def test_vector_store_operations(self):
        """Test 2: Vector store operations"""
        print(f"\n{BLUE}🧪 Test 2: Vector Store Operations{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Vector Store Operations", False, "Pipeline not initialized")
        
        try:
            # Test indexing
            initial_stats = self.pipeline.vector_store.get_stats()
            
            # Index test transcript
            transcript_path = "test_transcripts/test-course/neural-networks.md"
            chunks = self.pipeline.vector_store.index_transcript(transcript_path)
            
            # Index test note
            note_path = "test_knowledge/test-course/neural-networks.md"
            note_success = self.pipeline.vector_store.index_knowledge_note(note_path)
            
            # Test search
            search_results = self.pipeline.vector_store.search("neural networks", "transcripts", limit=3)
            
            # Verify results
            if chunks > 0 and note_success and len(search_results) > 0:
                details = f"Indexed {chunks} chunks, note indexed, {len(search_results)} search results"
                return self.log_test("Vector Store Operations", True, details)
            else:
                return self.log_test("Vector Store Operations", False, "Operations failed")
                
        except Exception as e:
            return self.log_test("Vector Store Operations", False, f"Error: {e}")
    
    def test_context_generation(self):
        """Test 3: Context generation"""
        print(f"\n{BLUE}🧪 Test 3: Context Generation{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Context Generation", False, "Pipeline not initialized")
        
        try:
            # Test course folder detection
            course_folders = self.pipeline.context_agent.find_course_folders()
            
            # Test global context generation
            global_context = self.pipeline.context_agent.generate_global_context()
            
            # Verify context structure
            required_keys = ["context_type", "generated_at", "courses", "summary"]
            context_valid = all(key in global_context for key in required_keys)
            
            if len(course_folders) >= 0 and context_valid:
                details = f"Found {len(course_folders)} courses, context generated"
                return self.log_test("Context Generation", True, details)
            else:
                return self.log_test("Context Generation", False, "Context generation failed")
                
        except Exception as e:
            return self.log_test("Context Generation", False, f"Error: {e}")
    
    def test_enhancement_process(self):
        """Test 4: Enhancement process"""
        print(f"\n{BLUE}🧪 Test 4: Enhancement Process{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Enhancement Process", False, "Pipeline not initialized")
        
        try:
            # Generate global context for enhancement
            global_context = self.pipeline.context_agent.generate_global_context()
            
            # Test concept extraction
            note_path = "test_knowledge/test-course/neural-networks.md"
            with open(note_path, 'r') as f:
                note_content = f.read()
            
            concepts = self.pipeline.enhancement_agent.extract_concepts_from_note(note_content)
            
            # Test related content retrieval
            related_content = self.pipeline.enhancement_agent.get_related_content(
                note_path, concepts[:3], limit=3
            )
            
            # Test enhancement preview (without actually enhancing)
            if global_context:
                preview = self.pipeline.enhancement_agent.preview_enhancement(note_path, global_context)
                preview_success = len(preview) > len(note_content)
            else:
                preview_success = False
            
            if len(concepts) > 0 and isinstance(related_content, dict) and preview_success:
                details = f"Extracted {len(concepts)} concepts, enhanced content"
                return self.log_test("Enhancement Process", True, details)
            else:
                return self.log_test("Enhancement Process", False, "Enhancement failed")
                
        except Exception as e:
            return self.log_test("Enhancement Process", False, f"Error: {e}")
    
    def test_search_functionality(self):
        """Test 5: Search functionality"""
        print(f"\n{BLUE}🧪 Test 5: Search Functionality{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Search Functionality", False, "Pipeline not initialized")
        
        try:
            # Test various search queries
            search_tests = [
                ("neural networks", "transcripts", 3),
                ("machine learning", "transcripts", 2),
                ("deep learning", "knowledge_notes", 2)
            ]
            
            search_results = []
            for query, collection, limit in search_tests:
                results = self.pipeline.vector_store.search(query, collection, limit)
                search_results.append(len(results))
            
            # Test cross-collection search
            total_results = sum(search_results)
            
            if total_results > 0:
                details = f"Search successful: {search_results} results across collections"
                return self.log_test("Search Functionality", True, details)
            else:
                return self.log_test("Search Functionality", False, "No search results")
                
        except Exception as e:
            return self.log_test("Search Functionality", False, f"Error: {e}")
    
    def test_performance_metrics(self):
        """Test 6: Performance metrics"""
        print(f"\n{BLUE}🧪 Test 6: Performance Metrics{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Performance Metrics", False, "Pipeline not initialized")
        
        try:
            # Time vector store operations
            start_time = time.time()
            stats = self.pipeline.vector_store.get_stats()
            stats_time = time.time() - start_time
            
            # Time search operation
            start_time = time.time()
            search_results = self.pipeline.vector_store.search("test query", "transcripts", 5)
            search_time = time.time() - start_time
            
            # Time context generation
            start_time = time.time()
            course_folders = self.pipeline.context_agent.find_course_folders()
            context_time = time.time() - start_time
            
            # Performance thresholds
            stats_ok = stats_time < 1.0
            search_ok = search_time < 5.0
            context_ok = context_time < 2.0
            
            if stats_ok and search_ok and context_ok:
                details = f"Stats: {stats_time:.3f}s, Search: {search_time:.3f}s, Context: {context_time:.3f}s"
                return self.log_test("Performance Metrics", True, details)
            else:
                details = f"Performance issues detected"
                return self.log_test("Performance Metrics", False, details)
                
        except Exception as e:
            return self.log_test("Performance Metrics", False, f"Error: {e}")
    
    def test_data_integrity(self):
        """Test 7: Data integrity"""
        print(f"\n{BLUE}🧪 Test 7: Data Integrity{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Data Integrity", False, "Pipeline not initialized")
        
        try:
            # Check vector store stats consistency
            stats = self.pipeline.vector_store.get_stats()
            
            # Verify indexed content matches files
            transcript_files = []
            note_files = []
            
            # Count actual files
            for test_folder in ["test_transcripts", TRANSCRIPTS_FOLDER]:
                if os.path.exists(test_folder):
                    for root, _, files in os.walk(test_folder):
                        transcript_files.extend([f for f in files if f.endswith('.md')])
            
            for test_folder in ["test_knowledge", KNOWLEDGE_BASE_FOLDER]:
                if os.path.exists(test_folder):
                    for root, _, files in os.walk(test_folder):
                        note_files.extend([f for f in files if f.endswith('.md')])
            
            # Check consistency (allowing for chunking in transcripts)
            transcripts_consistent = stats['transcripts'] > 0
            notes_consistent = stats['knowledge_notes'] >= len(note_files) if note_files else True
            
            if transcripts_consistent and notes_consistent:
                details = f"Stats consistent: {stats['transcripts']} transcript chunks, {stats['knowledge_notes']} notes"
                return self.log_test("Data Integrity", True, details)
            else:
                details = f"Data inconsistency detected"
                return self.log_test("Data Integrity", False, details)
                
        except Exception as e:
            return self.log_test("Data Integrity", False, f"Error: {e}")
    
    def test_error_handling(self):
        """Test 8: Error handling"""
        print(f"\n{BLUE}🧪 Test 8: Error Handling{RESET}")
        
        if not self.pipeline or not self.pipeline.initialized:
            return self.log_test("Error Handling", False, "Pipeline not initialized")
        
        try:
            # Test with non-existent files
            error_tests = []
            
            # Test indexing non-existent file
            try:
                chunks = self.pipeline.vector_store.index_transcript("non_existent_file.md")
                error_tests.append(chunks == 0)  # Should return 0, not crash
            except:
                error_tests.append(False)
            
            # Test searching empty collection
            try:
                results = self.pipeline.vector_store.search("test", "non_existent_collection", 5)
                error_tests.append(isinstance(results, list))  # Should return empty list
            except:
                error_tests.append(True)  # Exception is also acceptable
            
            # Test context generation with no data
            try:
                context = self.pipeline.context_agent.generate_global_context("non_existent_course")
                error_tests.append(isinstance(context, dict))  # Should return dict
            except:
                error_tests.append(False)
            
            error_handling_ok = sum(error_tests) >= len(error_tests) * 0.6  # 60% success rate
            
            if error_handling_ok:
                details = f"Error handling tests: {sum(error_tests)}/{len(error_tests)} passed"
                return self.log_test("Error Handling", True, details)
            else:
                details = f"Poor error handling: {sum(error_tests)}/{len(error_tests)} passed"
                return self.log_test("Error Handling", False, details)
                
        except Exception as e:
            return self.log_test("Error Handling", False, f"Unexpected error: {e}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print(f"{BLUE}🚀 Starting Comprehensive Test Suite{RESET}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Setup
        setup_ok = self.create_test_data()
        if not setup_ok:
            print(f"{RED}❌ Test setup failed, aborting{RESET}")
            return
        
        # Core tests
        tests = [
            self.test_pipeline_initialization,
            self.test_vector_store_operations,
            self.test_context_generation,
            self.test_enhancement_process,
            self.test_search_functionality,
            self.test_performance_metrics,
            self.test_data_integrity,
            self.test_error_handling
        ]
        
        # Run tests
        for test_func in tests:
            test_func()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Generate report
        elapsed_time = time.time() - start_time
        self.generate_test_report(elapsed_time)
    
    def generate_test_report(self, elapsed_time: float):
        """Generate comprehensive test report"""
        print(f"\n{BLUE}📊 Test Report{RESET}")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {GREEN}{passed_tests}{RESET}")
        print(f"Failed: {RED}{failed_tests}{RESET}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Execution Time: {elapsed_time:.2f} seconds")
        
        # Detailed results
        print(f"\n{BLUE}Detailed Results:{RESET}")
        for result in self.test_results:
            status = f"{GREEN}✓{RESET}" if result['passed'] else f"{RED}✗{RESET}"
            print(f"  {status} {result['test']}")
            if result['details']:
                print(f"    {result['details']}")
        
        # Overall assessment
        print(f"\n{BLUE}Assessment:{RESET}")
        if success_rate >= 90:
            print(f"{GREEN}🎉 Excellent! System is production-ready{RESET}")
        elif success_rate >= 75:
            print(f"{YELLOW}⚠️  Good! Minor issues to address{RESET}")
        elif success_rate >= 50:
            print(f"{YELLOW}🔧 Fair! Significant improvements needed{RESET}")
        else:
            print(f"{RED}❌ Poor! Major issues require attention{RESET}")
        
        # Save report
        report_data = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate,
                "execution_time": elapsed_time
            },
            "results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Run the comprehensive test suite"""
    test_suite = ComprehensiveTestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()