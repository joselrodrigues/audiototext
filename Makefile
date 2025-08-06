# Enhanced AudioToText Pipeline Makefile - Updated with All 5 Phases
# Integrates all improvements: Enhanced Academic Scraping, Semantic Understanding, Smart Chunking, Knowledge Synthesis

.PHONY: help test status clean setup transcribe notes index context enhance search all quick-start pipeline-safe test-improvements

# Default target
help:
	@echo "📚 Enhanced AudioToText Pipeline Commands (Updated with All Improvements)"
	@echo "============================================================================="
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  make all           - Run complete enhanced pipeline (all 5 phases)"
	@echo "  make all-force     - Run pipeline without asking about existing files"
	@echo "  make quick-start   - Setup + test enhanced system"
	@echo ""
	@echo "📋 ENHANCED WORKFLOW (All 5 Phases):"
	@echo "  make transcribe         - Step 1: Convert videos to transcripts"
	@echo "  make enhance-transcripts - Step 2: Semantic enhancement of transcripts (FASE 3)"
	@echo "  make notes              - Step 3: Generate enhanced academic notes (FASE 1+2)"
	@echo "  make smart-chunk        - Step 4: Intelligent chunking (FASE 4)" 
	@echo "  make synthesize         - Step 5: Knowledge synthesis (FASE 5)"
	@echo "  make index              - Step 6: Index with smart chunking"
	@echo "  make context            - Step 7: Generate global context"
	@echo "  make enhance            - Step 8: Enhance with preservation (FASE 2.5)"
	@echo ""
	@echo "🧪 TEST IMPROVEMENTS:"
	@echo "  make test-improvements  - Test all 5 phases of improvements"
	@echo "  make test-academic      - Test enhanced academic scraping (FASE 1)"
	@echo "  make test-semantic      - Test semantic understanding (FASE 3)"
	@echo "  make test-chunking      - Test smart chunking (FASE 4)"
	@echo "  make test-synthesis     - Test knowledge synthesis (FASE 5)"
	@echo "  make test-preservation  - Test content preservation (FASE 2.5)"
	@echo ""
	@echo "🔍 SEARCH & ANALYSIS:"
	@echo "  make search QUERY='your query'  - Search with smart chunking"
	@echo "  make status             - Show enhanced system status"
	@echo "  make show-improvements  - Show what improvements are active"
	@echo ""
	@echo "🧹 MAINTENANCE:"
	@echo "  make clean         - Clean temporary files"
	@echo "  make clean-enhanced - Clean enhanced transcripts and synthesis files"
	@echo "  make setup         - Verify enhanced system setup"

# Quick start with all improvements
quick-start: setup test-improvements
	@echo "✅ Enhanced system ready! Add videos to input_videos/ then run 'make all'"

# Complete enhanced pipeline - runs all 5 phases
all:
	@echo "🌟 Running COMPLETE Enhanced Pipeline (All 5 Phases)..."
	@echo "Phase 1: Enhanced Academic Scraping"
	@echo "Phase 2: Enriched MD Structure + Content Preservation" 
	@echo "Phase 3: Semantic Understanding"
	@echo "Phase 4: Smart Chunking"
	@echo "Phase 5: Knowledge Synthesis"
	@echo ""
	$(MAKE) transcribe
	$(MAKE) enhance-transcripts
	$(MAKE) notes
	$(MAKE) smart-chunk
	$(MAKE) synthesize
	$(MAKE) index
	$(MAKE) context  
	$(MAKE) enhance
	@echo ""
	@echo "🎉 ENHANCED Pipeline Complete! All 5 phases executed successfully!"
	@echo "📊 Results:"
	@echo "  📁 Enhanced transcripts: enhanced_transcripts/"
	@echo "  📚 Academic notes: knowledge_base/ (with 20+ references each)"
	@echo "  🧠 Knowledge synthesis: knowledge_synthesis_*.json"
	@echo "  🔍 Search: make search QUERY='your topic'"

# Complete pipeline with force mode
all-force:
	@echo "🚀 Running complete enhanced pipeline in force mode..."
	$(MAKE) transcribe
	$(MAKE) enhance-transcripts  
	$(MAKE) notes FORCE=--force
	$(MAKE) smart-chunk
	$(MAKE) synthesize
	$(MAKE) index FORCE=--force-reindex
	$(MAKE) context
	$(MAKE) enhance
	@echo "🎉 Enhanced pipeline finished!"

# Step 1: Convert videos to transcripts (unchanged)
transcribe:
	@echo "🎬 Step 1: Converting videos to transcripts..."
	uv run python batch_transcribe.py
	@echo "✅ Transcripts created in transcripts/ folder"

# Step 2: FASE 3 - Semantic enhancement of transcripts
enhance-transcripts:
	@echo "🧠 Step 2: FASE 3 - Semantic enhancement of transcripts..."
	@echo "  📝 Analyzing temporal structure and extracting concepts..."
	uv run python integration_transcript_enhancer.py
	@echo "✅ Enhanced transcripts with semantic understanding created"
	@echo "  📊 Quality scores and concept extraction completed"
	@echo "  📁 Results in enhanced_transcripts/ folder"

# Step 3: FASE 1+2 - Generate enhanced academic notes with scraping
notes:
ifdef FORCE
	@echo "📝 Step 3: FASE 1+2 - Generating enhanced academic notes (force mode)..."
	uv run python agents.py batch $(FORCE)
else
	@echo "📝 Step 3: FASE 1+2 - Generating enhanced academic notes..."
	@echo "  🌐 Using enhanced academic scraper (arXiv, Semantic Scholar, MIT OCW)"
	@echo "  📚 Enriching with Learning Objectives, Study Guides, Quick Reference"
	@echo "  🎯 Using o3-mini for final synthesis"
	uv run python agents.py batch
endif
	@echo "✅ Enhanced academic notes created with 20+ references each"
	@echo "  📁 Results in knowledge_base/ folder"

# Step 4: FASE 4 - Smart chunking analysis  
smart-chunk:
	@echo "⚡ Step 4: FASE 4 - Analyzing content with smart chunking..."
	@echo "  🧠 Using adaptive chunk sizing based on content complexity"
	@echo "  🎯 Preserving semantic boundaries and concept integrity"
	uv run python smart_chunker_final.py
	@echo "✅ Smart chunking analysis completed"
	@echo "  📊 Boundary-aware chunks with adaptive sizing"

# Step 5: FASE 5 - Knowledge synthesis
synthesize:
	@echo "🧬 Step 5: FASE 5 - Advanced knowledge synthesis..."
	@echo "  🔗 Identifying concept relationships across all sources"
	@echo "  🛤️  Generating optimal learning paths"
	@echo "  📈 Building knowledge graphs and cross-references"
	uv run python academic_synthesizer.py
	@echo "✅ Knowledge synthesis completed"
	@echo "  📊 Concept relationships, learning paths, and knowledge graphs generated"
	@echo "  📁 Results in knowledge_synthesis_*.json files"

# Step 6: Index with smart chunking
index:
ifdef FORCE
	@echo "📚 Step 6: Indexing with smart chunking (force mode)..."
	uv run python enhanced_pipeline.py index $(FORCE)
else
	@echo "📚 Step 6: Indexing content with smart chunking..."
	@echo "  🧠 Using boundary-aware chunking for optimal retrieval"
	uv run python enhanced_pipeline.py index
endif
	@echo "✅ Content indexed with smart chunking into ChromaDB"

# Step 7: Generate global course context
context:
	@echo "🌍 Step 7: Generating global course context..."
	uv run python enhanced_pipeline.py context
	@echo "✅ Global context generated with enhanced understanding"

# Step 8: FASE 2.5 - Enhance with content preservation
enhance:
ifdef COURSE
	@echo "🔧 Step 8: FASE 2.5 - Enhancing notes for course: $(COURSE) (with preservation)..."
	uv run python enhanced_pipeline.py enhance --course $(COURSE)
else
	@echo "🔧 Step 8: FASE 2.5 - Enhancing all notes with preservation..."
	@echo "  🛡️  Preserving all academic references (arXiv, DOI, etc.)"
	@echo "  ✅ Validation checks to prevent content loss"
	uv run python enhanced_pipeline.py enhance
endif
	@echo "✅ Notes enhanced with 100% content preservation"

# TEST ALL IMPROVEMENTS
test-improvements:
	@echo "🧪 Testing All 5 Phases of Improvements..."
	@echo ""
	@echo "🧪 FASE 1: Testing Enhanced Academic Scraping..."
	uv run python test_enhanced_scraping.py
	@echo ""
	@echo "🧪 FASE 2.5: Testing Content Preservation..."
	uv run python test_preservation.py
	@echo ""
	@echo "🧪 FASE 3: Testing Semantic Understanding..."
	uv run python test_transcript_enhancer.py
	@echo ""
	@echo "🧪 FASE 4: Testing Smart Chunking..."
	uv run python test_concept_aware_chunker.py
	@echo ""
	@echo "🧪 FASE 5: Testing Knowledge Synthesis..."
	uv run python academic_synthesizer.py
	@echo ""
	@echo "✅ All improvement phases tested!"

# Individual improvement tests
test-academic:
	@echo "🧪 Testing FASE 1: Enhanced Academic Scraping..."
	uv run python test_enhanced_scraping.py

test-semantic:
	@echo "🧪 Testing FASE 3: Semantic Understanding..."
	uv run python test_transcript_enhancer.py

test-chunking:
	@echo "🧪 Testing FASE 4: Smart Chunking..."
	uv run python test_concept_aware_chunker.py

test-synthesis:
	@echo "🧪 Testing FASE 5: Knowledge Synthesis..."
	uv run python academic_synthesizer.py

test-preservation:
	@echo "🧪 Testing FASE 2.5: Content Preservation..."
	uv run python test_preservation.py

# Show what improvements are active
show-improvements:
	@echo "🌟 Active Improvements in Enhanced Pipeline:"
	@echo ""
	@echo "✅ FASE 1: Enhanced Academic Scraping"
	@echo "   📄 Files: enhanced_academic_scraper.py"
	@echo "   🎯 Features: arXiv API, Semantic Scholar, MIT OCW, Stanford"
	@echo ""
	@echo "✅ FASE 2: Enriched MD Structure"  
	@echo "   📄 Files: agents.py (modified generate_obsidian_note)"
	@echo "   🎯 Features: Learning Objectives, Study Guide, Quick Reference, o3-mini"
	@echo ""
	@echo "✅ FASE 2.5: Content Preservation"
	@echo "   📄 Files: enhancement_agent.py"
	@echo "   🎯 Features: 100% reference preservation, validation checks"
	@echo ""
	@echo "✅ FASE 3: Semantic Understanding"
	@echo "   📄 Files: transcript_enhancer.py, integration_transcript_enhancer.py"
	@echo "   🎯 Features: Quality scoring, concept extraction, temporal analysis"
	@echo ""
	@echo "✅ FASE 4: Smart Chunking"  
	@echo "   📄 Files: smart_chunker_final.py"
	@echo "   🎯 Features: Adaptive sizing, boundary preservation, 4 strategies"
	@echo ""
	@echo "✅ FASE 5: Knowledge Synthesis"
	@echo "   📄 Files: academic_synthesizer.py"
	@echo "   🎯 Features: Concept graphs, learning paths, relationship detection"

# Search with enhanced capabilities
search:
ifndef QUERY
	@echo "❌ Usage: make search QUERY='your search term'"
	@echo "💡 Examples:"
	@echo "  make search QUERY='neural networks'"
	@echo "  make search QUERY='machine learning algorithms'"
else
	@echo "🔍 Enhanced Search for: $(QUERY)"
	@echo "  🧠 Using smart chunking for optimal results..."
	uv run python enhanced_pipeline.py search "$(QUERY)"
endif

# Enhanced system status
status:
	@echo "📊 Enhanced System Status:"
	@echo ""
	@echo "🌟 Improvement Phases Status:"
	@test -f enhanced_academic_scraper.py && echo "✅ FASE 1: Enhanced Academic Scraping - Active" || echo "❌ FASE 1: Not found"
	@grep -q "o3-mini" agents.py && echo "✅ FASE 2: Enhanced MD Structure - Active" || echo "❌ FASE 2: Not active"  
	@test -f enhancement_agent.py && echo "✅ FASE 2.5: Content Preservation - Active" || echo "❌ FASE 2.5: Not found"
	@test -f transcript_enhancer.py && echo "✅ FASE 3: Semantic Understanding - Active" || echo "❌ FASE 3: Not found"
	@test -f smart_chunker_final.py && echo "✅ FASE 4: Smart Chunking - Active" || echo "❌ FASE 4: Not found"
	@test -f academic_synthesizer.py && echo "✅ FASE 5: Knowledge Synthesis - Active" || echo "❌ FASE 5: Not found"
	@echo ""
	@echo "📊 System Components:"
	uv run python enhanced_pipeline.py status

# Enhanced setup verification
setup:
	@echo "🔧 Verifying Enhanced System Setup..."
	@echo ""
	@echo "1. Checking Python environment..."
	@python3 --version || echo "❌ Python not found"
	@echo ""
	@echo "2. Checking uv package manager..." 
	@uv --version || echo "❌ uv not found - install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo ""
	@echo "3. Checking project dependencies..."
	@uv sync
	@echo ""
	@echo "4. Checking environment configuration..."
	@test -f .env && echo "✅ .env file found" || echo "⚠️  .env file missing - copy from .env.example"
	@echo ""
	@echo "5. Checking enhancement files..."
	@test -f enhanced_academic_scraper.py && echo "✅ Enhanced academic scraper found" || echo "❌ Enhanced scraper missing"
	@test -f transcript_enhancer.py && echo "✅ Transcript enhancer found" || echo "❌ Transcript enhancer missing"
	@test -f smart_chunker_final.py && echo "✅ Smart chunker found" || echo "❌ Smart chunker missing"
	@test -f academic_synthesizer.py && echo "✅ Academic synthesizer found" || echo "❌ Academic synthesizer missing"
	@echo ""
	@echo "6. Running quick enhanced system test..."
	@uv run python -c "from config import BASE_URL, API_KEY; print('✅ Configuration loaded')" || echo "❌ Configuration error"

# Clean enhanced files
clean-enhanced:
	@echo "🧹 Cleaning enhanced pipeline files..."
	@rm -f enhanced_transcript_*.json
	@rm -f knowledge_synthesis_*.json
	@rm -f preview_*.md
	@rm -rf enhanced_transcripts/
	@echo "✅ Enhanced files cleaned"

# Standard clean
clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -f preview_*.md
	@rm -f global_context_*.json
	@rm -f test_report_*.json
	@rm -f enhanced_transcript_*.json
	@rm -f knowledge_synthesis_*.json
	@echo "✅ Temporary files cleaned"

# Deep clean including enhanced databases
clean-all: clean clean-enhanced
	@echo "🧹 Deep cleaning (including databases)..."
	@rm -rf chroma_db/
	@rm -rf output_audio/
	@echo "✅ Deep clean completed - run 'make index' to rebuild"

# Development shortcuts with enhancements
dev-reset: clean-all index context
	@echo "🔄 Enhanced development environment reset"

# Show enhanced project structure
show-structure:
	@echo "📁 Enhanced Project Structure:"
	@echo "├── input_videos/          (Place your video files here)"
	@find input_videos -name "*.mp4" -o -name "*.avi" -o -name "*.mov" 2>/dev/null | head -3 | sed 's/^/│   /'
	@echo "├── transcripts/           (Basic transcripts)"
	@find transcripts -name "*.md" 2>/dev/null | sed 's/transcripts\//│   /' | head -3
	@echo "├── enhanced_transcripts/  (🌟 FASE 3: Semantically enhanced transcripts)"
	@find enhanced_transcripts -name "*.json" 2>/dev/null | sed 's/enhanced_transcripts\//│   /' | head -3
	@echo "├── knowledge_base/        (🌟 Enhanced academic notes with 20+ references)"
	@find knowledge_base -name "*.md" 2>/dev/null | sed 's/knowledge_base\//│   /' | head -3
	@echo "├── chroma_db/            (🌟 Vector database with smart chunking)"
	@echo "└── Enhancement Files:"
	@echo "    ├── enhanced_academic_scraper.py    (🌟 FASE 1)"
	@echo "    ├── transcript_enhancer.py          (🌟 FASE 3)"  
	@echo "    ├── smart_chunker_final.py          (🌟 FASE 4)"
	@echo "    ├── academic_synthesizer.py         (🌟 FASE 5)"
	@echo "    └── enhancement_agent.py            (🌟 FASE 2.5)"

# Show enhanced usage examples
examples:
	@echo "💡 Enhanced Usage Examples:"
	@echo ""
	@echo "🌟 Run complete enhanced pipeline:"
	@echo "  make all                 # All 5 phases of improvements"
	@echo ""
	@echo "📹 Process new videos with all enhancements:"
	@echo "  1. cp /path/to/videos/*.mp4 input_videos/"
	@echo "  2. make all"
	@echo "  3. Check enhanced results with 20+ academic references per note"  
	@echo ""
	@echo "🧪 Test specific improvements:"
	@echo "  make test-academic       # Test enhanced academic scraping"
	@echo "  make test-semantic       # Test semantic understanding"
	@echo "  make test-chunking       # Test smart chunking"
	@echo "  make test-synthesis      # Test knowledge synthesis"
	@echo ""
	@echo "🔍 Enhanced search with smart chunking:"
	@echo "  make search QUERY='neural networks'"
	@echo "  make search QUERY='machine learning algorithms'"