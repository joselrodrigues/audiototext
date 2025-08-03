#!/usr/bin/env python3
"""Run the complete enhanced pipeline without timeout issues"""

import subprocess
import sys
import time
from pathlib import Path
import os

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class PipelineRunner:
    """Run pipeline steps with proper error handling and no timeouts"""
    
    def __init__(self):
        self.steps_completed = []
        self.start_time = time.time()
        
    def run_command(self, command: str, description: str, skip_if_exists=None):
        """Run a command with progress tracking"""
        print(f"\n{BLUE}▶ {description}{RESET}")
        print(f"  Command: {command}")
        
        # Check if we should skip this step
        if skip_if_exists and os.path.exists(skip_if_exists):
            print(f"  {YELLOW}⏭️  Skipping - {skip_if_exists} already exists{RESET}")
            return True
            
        try:
            # Run command without timeout
            result = subprocess.run(
                command, 
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✅ Success{RESET}")
                self.steps_completed.append(description)
                return True
            else:
                print(f"  {RED}❌ Failed with exit code {result.returncode}{RESET}")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"  {RED}❌ Exception: {e}{RESET}")
            return False
    
    def check_prerequisites(self):
        """Check that everything is ready to run"""
        print(f"{BLUE}🔍 Checking prerequisites...{RESET}")
        
        checks = []
        
        # Check for .env file
        if os.path.exists('.env'):
            print(f"  {GREEN}✓{RESET} .env file found")
            checks.append(True)
        else:
            print(f"  {RED}✗{RESET} .env file missing")
            checks.append(False)
            
        # Check for input videos
        video_count = 0
        if os.path.exists('input_videos'):
            for ext in ['.mp4', '.avi', '.mov', '.mkv']:
                video_count += len(list(Path('input_videos').rglob(f'*{ext}')))
        
        if video_count > 0:
            print(f"  {GREEN}✓{RESET} Found {video_count} video files")
            checks.append(True)
        else:
            print(f"  {YELLOW}⚠{RESET} No video files found in input_videos/")
            # This is not a hard requirement
            
        return all(checks)
    
    def run_complete_pipeline(self):
        """Run the complete pipeline step by step"""
        print(f"{BLUE}🚀 Enhanced AudioToText Pipeline Runner{RESET}")
        print("=" * 60)
        
        if not self.check_prerequisites():
            print(f"\n{RED}❌ Prerequisites not met. Please fix issues above.{RESET}")
            return False
        
        # Define pipeline steps
        steps = [
            {
                'command': 'uv run python batch_transcribe.py',
                'description': 'Step 1: Convert videos to transcripts',
                'skip_if': None  # Always run if there are new videos
            },
            {
                'command': 'uv run python agents.py batch',
                'description': 'Step 2: Generate educational notes (this may take several minutes)',
                'skip_if': None  # Could add logic to skip if notes exist
            },
            {
                'command': 'uv run python enhanced_pipeline.py index',
                'description': 'Step 3: Index content into vector database',
                'skip_if': None
            },
            {
                'command': 'uv run python enhanced_pipeline.py context',
                'description': 'Step 4: Generate global course context',
                'skip_if': None
            },
            {
                'command': 'uv run python enhanced_pipeline.py enhance',
                'description': 'Step 5: Enhance notes with context',
                'skip_if': None
            }
        ]
        
        # Run each step
        all_success = True
        for step in steps:
            success = self.run_command(
                step['command'], 
                step['description'],
                step.get('skip_if')
            )
            
            if not success:
                print(f"\n{RED}❌ Pipeline failed at: {step['description']}{RESET}")
                all_success = False
                break
            
            # Small delay between steps
            time.sleep(1)
        
        # Summary
        elapsed = time.time() - self.start_time
        print(f"\n{BLUE}📊 Pipeline Summary{RESET}")
        print("=" * 60)
        print(f"Steps completed: {len(self.steps_completed)}/{len(steps)}")
        for step in self.steps_completed:
            print(f"  {GREEN}✓{RESET} {step}")
        print(f"\nTotal time: {elapsed/60:.1f} minutes")
        
        if all_success:
            print(f"\n{GREEN}🎉 Pipeline completed successfully!{RESET}")
            print(f"\n📁 Your enhanced notes are in: knowledge_base/")
            print(f"🔍 Try searching: uv run python enhanced_pipeline.py search 'your topic'")
        else:
            print(f"\n{YELLOW}⚠️  Pipeline partially completed{RESET}")
            print(f"You can continue from where it stopped by running individual commands.")
            
        return all_success
    
    def run_quick_index(self):
        """Just run indexing and enhancement (for existing content)"""
        print(f"{BLUE}🚀 Quick Index & Enhancement{RESET}")
        print("=" * 60)
        
        steps = [
            {
                'command': 'uv run python enhanced_pipeline.py index --force-reindex',
                'description': 'Reindex all content'
            },
            {
                'command': 'uv run python enhanced_pipeline.py context',
                'description': 'Generate global context'
            },
            {
                'command': 'uv run python enhanced_pipeline.py enhance',
                'description': 'Enhance notes'
            }
        ]
        
        for step in steps:
            if not self.run_command(step['command'], step['description']):
                return False
                
        return True

def main():
    """Main entry point"""
    runner = PipelineRunner()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        # Just do indexing and enhancement
        success = runner.run_quick_index()
    else:
        # Run complete pipeline
        success = runner.run_complete_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()