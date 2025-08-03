# Enhanced AudioToText Pipeline Makefile
# Makes it easy to run the complete workflow

.PHONY: help test status clean setup transcribe notes index context enhance search all quick-start pipeline-safe

# Default target
help:
	@echo "📚 Enhanced AudioToText Pipeline Commands"
	@echo "=========================================="
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  make all           - Run complete pipeline (videos → enhanced notes)"
	@echo "  make quick-start   - Setup + test system"
	@echo ""
	@echo "📋 STEP-BY-STEP WORKFLOW:"
	@echo "  make transcribe    - Step 1: Convert videos to transcripts"
	@echo "  make notes         - Step 2: Generate basic educational notes"
	@echo "  make index         - Step 3: Index content into vector database"  
	@echo "  make context       - Step 4: Generate global course context"
	@echo "  make enhance       - Step 5: Enhance notes with context"
	@echo ""
	@echo "🔍 SEARCH & ANALYSIS:"
	@echo "  make search QUERY='your query'  - Search content"
	@echo "  make status        - Show system status"
	@echo ""
	@echo "🧪 TESTING & MAINTENANCE:"
	@echo "  make test          - Run quick tests"
	@echo "  make test-full     - Run comprehensive tests"
	@echo "  make clean         - Clean temporary files"
	@echo "  make setup         - Verify system setup"
	@echo ""
	@echo "💡 EXAMPLES:"
	@echo "  make search QUERY='neural networks'"
	@echo "  make enhance COURSE='machine-learning'"
	@echo "  make preview FILE='knowledge_base/my-note.md'"

# Quick start - setup and test
quick-start: setup test
	@echo "✅ System ready! Add videos to input_videos/ then run 'make all'"

# Run pipeline without timeout issues
pipeline-safe:
	@echo "🛡️ Running pipeline in safe mode (no timeouts)..."
	@uv run python run_pipeline.py

# Complete pipeline - runs everything without timeouts
all:
	@echo "🚀 Running complete pipeline (timeout-safe)..."
	@uv run python run_pipeline.py
	@echo ""
	@echo "🎉 Complete pipeline finished!"
	@echo "📁 Check knowledge_base/ for enhanced educational notes"
	@echo "🔍 Use 'make search QUERY=\"your query\"' to search content"

# Step 1: Convert videos to transcripts
transcribe:
	@echo "🎬 Step 1: Converting videos to transcripts..."
	uv run python batch_transcribe.py
	@echo "✅ Transcripts created in transcripts/ folder"

# Step 2: Generate basic educational notes
notes:
	@echo "📝 Step 2: Generating educational notes with web research..."
	uv run python agents.py batch
	@echo "✅ Basic educational notes created in knowledge_base/ folder"

# Step 3: Index content into vector database
index:
	@echo "📚 Step 3: Indexing content into vector database..."
	uv run python enhanced_pipeline.py index
	@echo "✅ Content indexed into ChromaDB"

# Step 4: Generate global course context
context:
	@echo "🌍 Step 4: Generating global course context..."
	uv run python enhanced_pipeline.py context
	@echo "✅ Global context generated"

# Step 5: Enhance notes with context
enhance:
ifdef COURSE
	@echo "🔧 Step 5: Enhancing notes for course: $(COURSE)..."
	uv run python enhanced_pipeline.py enhance --course $(COURSE)
else
	@echo "🔧 Step 5: Enhancing all notes with global context..."
	uv run python enhanced_pipeline.py enhance
endif
	@echo "✅ Notes enhanced with context and cross-references"

# Force reindex everything
reindex:
	@echo "🔄 Force reindexing all content..."
	uv run python enhanced_pipeline.py index --force-reindex

# Preview enhancement for a specific file
preview:
ifndef FILE
	@echo "❌ Usage: make preview FILE='path/to/file.md'"
	@echo "📁 Available files:"
	@find knowledge_base -name "*.md" | head -5
	@echo "   ..."
else
	@echo "👀 Previewing enhancement for: $(FILE)"
	uv run python enhanced_pipeline.py enhance --preview $(FILE)
	@echo "✅ Preview saved - check preview_* file"
endif

# Search content
search:
ifndef QUERY
	@echo "❌ Usage: make search QUERY='your search term'"
	@echo "💡 Examples:"
	@echo "  make search QUERY='neural networks'"
	@echo "  make search QUERY='Big O notation'"
else
	@echo "🔍 Searching for: $(QUERY)"
	uv run python enhanced_pipeline.py search "$(QUERY)"
endif

# Search in specific collection
search-transcripts:
ifndef QUERY
	@echo "❌ Usage: make search-transcripts QUERY='your search term'"
else
	@echo "🔍 Searching transcripts for: $(QUERY)"
	uv run python enhanced_pipeline.py search "$(QUERY)" --collection transcripts
endif

search-notes:
ifndef QUERY
	@echo "❌ Usage: make search-notes QUERY='your search term'"
else
	@echo "🔍 Searching knowledge notes for: $(QUERY)"
	uv run python enhanced_pipeline.py search "$(QUERY)" --collection knowledge_notes
endif

# System status and diagnostics
status:
	@echo "📊 System Status:"
	uv run python enhanced_pipeline.py status

# Testing
test:
	@echo "🧪 Running quick tests (no API calls)..."
	uv run python test_quick.py

test-full:
	@echo "🧪 Running comprehensive tests (with API calls)..."
	uv run python test_comprehensive.py

# System setup verification
setup:
	@echo "🔧 Verifying system setup..."
	@echo "1. Checking Python environment..."
	@python3 --version || echo "❌ Python not found"
	@echo "2. Checking uv package manager..."
	@uv --version || echo "❌ uv not found - install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "3. Checking project dependencies..."
	@uv sync
	@echo "4. Checking environment configuration..."
	@test -f .env && echo "✅ .env file found" || echo "⚠️  .env file missing - copy from .env.example"
	@echo "5. Running quick system test..."
	@uv run python -c "from config import BASE_URL, API_KEY; print('✅ Configuration loaded')" || echo "❌ Configuration error"

# Development commands
diagnose:
	@echo "🔍 Running system diagnostics..."
	uv run python diagnose.py

# Migration from old system
migrate:
	@echo "🔄 Migrating from old system to enhanced pipeline..."
	uv run python migrate_to_enhanced.py

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -f preview_*.md
	@rm -f global_context_*.json
	@rm -f test_report_*.json
	@rm -f migration_*.json
	@rm -f cleanup_report_*.json
	@echo "✅ Temporary files cleaned"

# Clean everything (including databases)
clean-all: clean
	@echo "🧹 Deep cleaning (including databases)..."
	@rm -rf chroma_db/
	@rm -rf output_audio/
	@echo "✅ Deep clean completed - run 'make index' to rebuild"

# Development shortcuts
dev-reset: clean-all index context
	@echo "🔄 Development environment reset"

# Show project structure
show-structure:
	@echo "📁 Project Structure:"
	@echo "├── input_videos/     (Place your video files here)"
	@find input_videos -name "*.mp4" -o -name "*.avi" -o -name "*.mov" 2>/dev/null | head -3 | sed 's/^/│   /'
	@echo "├── transcripts/      (Generated transcripts organized by course)"
	@find transcripts -name "*.md" 2>/dev/null | sed 's/transcripts\//│   /' | head -5
	@echo "├── knowledge_base/   (Enhanced educational notes organized by course)"
	@find knowledge_base -name "*.md" 2>/dev/null | sed 's/knowledge_base\//│   /' | head -5
	@echo "└── chroma_db/        (Vector database)"

# Batch operations for courses
process-course:
ifndef COURSE
	@echo "❌ Usage: make process-course COURSE='course-name'"
else
	@echo "🎓 Processing course: $(COURSE)"
	uv run python enhanced_pipeline.py context --course $(COURSE)
	uv run python enhanced_pipeline.py enhance --course $(COURSE)
	@echo "✅ Course $(COURSE) processing completed"
endif

# Show available courses
show-courses:
	@echo "🎓 Available Courses:"
	@find transcripts -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sed 's/transcripts\///' | sed 's/^/  - /' || echo "  No courses found"

# Show usage examples
examples:
	@echo "💡 Usage Examples:"
	@echo ""
	@echo "📹 Process new videos:"
	@echo "  1. cp /path/to/videos/*.mp4 input_videos/"
	@echo "  2. make all"
	@echo ""
	@echo "🔍 Search content:"
	@echo "  make search QUERY='machine learning'"
	@echo "  make search QUERY='Big O notation'"
	@echo ""
	@echo "👀 Preview enhancements:"
	@echo "  make preview FILE='knowledge_base/my-lecture.md'"
	@echo ""
	@echo "🎓 Work with specific courses:"
	@echo "  make process-course COURSE='machine-learning'"
	@echo ""
	@echo "🧪 Test and maintain:"
	@echo "  make test"
	@echo "  make status"
	@echo "  make clean"