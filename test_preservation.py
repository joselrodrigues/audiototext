#!/usr/bin/env python3
"""Test suite for content preservation in enhancement process"""

import os
import tempfile
from pathlib import Path
from enhancement_agent import EnhancementAgent
from simple_vector_store import SimpleVectorStore

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class PreservationTest:
    """Test that enhancement preserves academic content"""
    
    def __init__(self):
        self.test_note_with_refs = """# Neural Networks - Comprehensive Study Notes

## 🎯 Learning Objectives
- Understand neural network architecture
- Master backpropagation algorithm
- Apply to real problems

## 📚 Prerequisites & Context
- Linear algebra basics
- Calculus understanding
- **Difficulty**: Intermediate

## Lecture Overview
This lecture covers neural networks fundamentals...

## Key Concepts Explained
### Neural Networks
#### Definition & Theory
Neural networks are computational models...

#### Common Misconceptions
- Networks don't exactly mimic brains
- Not always the best solution

#### Visual Understanding
Think of layers as filters...

## 🔬 Deep Dive Research

### Key Academic Papers
- Rumelhart, D. E., et al. (1986). Learning representations by back-propagating errors. Nature. DOI: 10.1038/323533a0
- LeCun, Y., et al. (1998). Gradient-based learning. Proceedings of the IEEE. arXiv:1998.12345
- Hinton, G., et al. (2012). Deep Neural Networks for Acoustic Modeling. arXiv:1209.3456v2

### University Course Materials
- MIT OCW: 6.034 Artificial Intelligence - Complete course materials
- Stanford CS231n: Convolutional Neural Networks for Visual Recognition

### Recent Developments (2022-2025)
- Zhang, L., & Wang, K. (2023). Efficient Training of Large Neural Networks. arXiv:2306.12345v3
- Smith, J., et al. (2024). Novel Architectures for Deep Learning. DOI: 10.1145/3567890

## 🎓 Study Guide

### Self-Assessment Questions
1. Can you explain backpropagation?
2. What are activation functions?
3. How do CNNs differ from RNNs?

### Practice Problems
- **Beginner**: Implement a perceptron
- **Intermediate**: Build a 2-layer network
- **Advanced**: Design a CNN architecture

### Mini Project Ideas
- Build a digit classifier
- Create a simple chatbot

## 📊 Quick Reference Card
| Concept | Definition | Key Formula |
|---------|-----------|-------------|
| Neuron | Basic unit | y = σ(Wx + b) |
| Backprop | Gradient calc | ∂L/∂w |

## References for Deep Dive

### Foundational Books
- Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press. ISBN: 978-0262035613
- Bishop, C. M. (2006). Pattern Recognition and Machine Learning. Springer. ISBN: 978-0387310732

### Online Resources
- Deep Learning Specialization on Coursera by Andrew Ng
- Fast.ai Practical Deep Learning Course

### Research Papers
- All papers listed in Deep Dive Research section above

## Tags
#neural-networks #deep-learning #comprehensive-study #university-level
"""
    
    def create_mock_context(self):
        """Create mock global context"""
        return {
            "courses": {
                "test-course": {
                    "course_name": "Machine Learning Fundamentals",
                    "course_description": "Introduction to ML concepts",
                    "main_topics": ["neural networks", "optimization", "classification"],
                    "concept_progression": {
                        "learning_path": ["basics", "neural nets", "deep learning"]
                    }
                }
            }
        }
    
    def test_enhancement_preservation(self):
        """Test that enhancement preserves all academic content"""
        print(f"{BLUE}Testing Academic Content Preservation{RESET}")
        
        # Create test environment
        vs = SimpleVectorStore()
        vs.connect()
        
        agent = EnhancementAgent(vs)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(self.test_note_with_refs)
            test_file = f.name
        
        try:
            # Mock global context
            global_context = self.create_mock_context()
            
            # Enhance the note
            result = agent.enhance_note_with_context(test_file, global_context)
            
            if result["status"] != "success" and result["status"] != "partial":
                print(f"  {RED}✗{RESET} Enhancement failed: {result.get('error', 'Unknown error')}")
                return False
            
            enhanced_content = result["enhanced_content"]
            
            # Validation checks
            checks = {
                "Learning Objectives preserved": "🎯 Learning Objectives" in enhanced_content,
                "Study Guide preserved": "🎓 Study Guide" in enhanced_content,
                "Deep Research preserved": "🔬 Deep Dive Research" in enhanced_content,
                "Quick Reference preserved": "📊 Quick Reference Card" in enhanced_content,
                "arXiv references preserved": enhanced_content.count("arXiv") >= 3,
                "DOI references preserved": enhanced_content.count("DOI") >= 2,
                "MIT OCW preserved": "MIT OCW" in enhanced_content,
                "Practice problems preserved": "Beginner" in enhanced_content and "Advanced" in enhanced_content,
                "Table preserved": "|" in enhanced_content and "Neuron" in enhanced_content
            }
            
            # Print results
            all_passed = True
            for check_name, passed in checks.items():
                status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
                print(f"  {status} {check_name}")
                if not passed:
                    all_passed = False
            
            # Check validation issues
            if result.get("validation_issues"):
                print(f"\n  {YELLOW}⚠ Validation issues detected:{RESET}")
                for issue in result["validation_issues"]:
                    print(f"    - {issue}")
            
            # Summary
            original_length = result["original_length"]
            enhanced_length = result["enhanced_length"]
            growth = ((enhanced_length - original_length) / original_length) * 100
            
            print(f"\n  {BLUE}Content Statistics:{RESET}")
            print(f"    Original: {original_length} chars")
            print(f"    Enhanced: {enhanced_length} chars")
            print(f"    Growth: {growth:.1f}%")
            
            return all_passed
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_reference_counting(self):
        """Test specific reference preservation"""
        print(f"\n{BLUE}Testing Reference Counting{RESET}")
        
        original = self.test_note_with_refs
        
        # Count references
        stats = {
            "arXiv papers": original.count("arXiv:"),
            "DOIs": original.count("DOI:"),
            "ISBNs": original.count("ISBN:"),
            "MIT courses": original.count("MIT OCW"),
            "Stanford courses": original.count("Stanford"),
            "Total papers in Deep Dive": len([line for line in original.split('\n') if line.strip().startswith('- ') and ('arXiv' in line or 'DOI' in line)])
        }
        
        print(f"  {BLUE}Original Reference Count:{RESET}")
        for ref_type, count in stats.items():
            print(f"    {ref_type}: {count}")
        
        expected_minimums = {
            "arXiv papers": 3,
            "DOIs": 2,
            "ISBNs": 2,
            "MIT courses": 1,
            "Total papers": 5
        }
        
        print(f"\n  {BLUE}Validation:{RESET}")
        all_valid = True
        for ref_type, expected in expected_minimums.items():
            actual = stats.get(ref_type, 0)
            passed = actual >= expected
            status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
            print(f"    {status} {ref_type}: {actual} (expected ≥ {expected})")
            if not passed:
                all_valid = False
        
        return all_valid


def main():
    """Run preservation tests"""
    print(f"{BLUE}🧪 Academic Content Preservation Test Suite{RESET}")
    print("=" * 60)
    
    tester = PreservationTest()
    
    tests = [
        ("Enhancement Preservation", tester.test_enhancement_preservation),
        ("Reference Counting", tester.test_reference_counting)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"  {RED}✗{RESET} {test_name} error: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{BLUE}📊 Test Summary{RESET}")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"{status} | {test_name}")
    
    print(f"\nTests: {passed_count}/{total_count} passed")
    
    if passed_count == total_count:
        print(f"\n{GREEN}✅ All preservation tests passed!{RESET}")
        print("Academic content will be preserved during enhancement.")
    else:
        print(f"\n{RED}❌ Some tests failed.{RESET}")
        print("Check the enhancement preservation logic.")


if __name__ == "__main__":
    main()