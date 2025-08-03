"""Simple vector store implementation using ChromaDB for AudioToText"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from config import (
    BASE_URL, 
    API_KEY,
    EMBEDDING_MODEL,
    CHUNK_SIZE
)


class SimpleVectorStore:
    """Simple vector store using ChromaDB for transcripts and knowledge base"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client"""
        self.persist_directory = persist_directory
        self.client = None
        self.collections = {}
        
        # Setup embedding function
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=API_KEY,
            api_base=BASE_URL,
            model_name=EMBEDDING_MODEL
        )
        
    def connect(self):
        """Connect to ChromaDB"""
        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Get or create collections
            self.collections["transcripts"] = self.client.get_or_create_collection(
                name="transcripts",
                embedding_function=self.embedding_fn,
                metadata={"description": "Video transcripts and subtitles"}
            )
            
            self.collections["knowledge_notes"] = self.client.get_or_create_collection(
                name="knowledge_notes", 
                embedding_function=self.embedding_fn,
                metadata={"description": "Processed academic notes"}
            )
            
            print(f"✅ Connected to ChromaDB at {self.persist_directory}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to ChromaDB: {e}")
            return False
    
    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        # Ensure step is at least 1 to avoid infinite loop
        step = max(1, chunk_size - overlap)
        
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
                
        return chunks
    
    def index_transcript(self, file_path: str, metadata: Dict[str, Any] = None) -> int:
        """Index a transcript file"""
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from file path
            path_parts = Path(file_path).parts
            course_folder = path_parts[-2] if len(path_parts) > 1 else "general"
            file_name = Path(file_path).stem
            
            # Determine content type
            content_type = "subtitle" if "subtitle" in file_name else "transcript"
            
            # Remove YAML front matter if present
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) > 2:
                    content = parts[2].strip()
            
            # Chunk the content
            chunks = self.chunk_text(content)
            
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                doc_metadata = {
                    "source_file": str(file_path),
                    "chunk_index": i,
                    "lecture_name": file_name,
                    "course_folder": course_folder,
                    "content_type": content_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {})
                }
                
                # Create unique ID
                chunk_id = hashlib.md5(f"{file_path}_{i}".encode()).hexdigest()
                
                documents.append(chunk)
                metadatas.append(doc_metadata)
                ids.append(chunk_id)
            
            # Add to collection
            if documents:
                self.collections["transcripts"].add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            print(f"✅ Indexed {len(chunks)} chunks from {file_path}")
            return len(chunks)
            
        except Exception as e:
            print(f"❌ Error indexing transcript {file_path}: {e}")
            return 0
    
    def index_knowledge_note(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Index a knowledge base note"""
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title (first # heading)
            title = "Untitled"
            for line in content.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            # Extract concepts (look for specific patterns)
            concepts = []
            if "Concepts covered:" in content:
                # Look for the concepts line in the output
                for line in content.split('\n'):
                    if line.startswith('Concepts covered:'):
                        concepts_text = line.replace('Concepts covered:', '').strip()
                        concepts = [c.strip() for c in concepts_text.split(',')]
                        break
            
            # Extract metadata
            path_parts = Path(file_path).parts
            lecture_name = Path(file_path).stem
            course_folder = path_parts[-2] if len(path_parts) > 1 else "general"
            
            doc_metadata = {
                "source_file": str(file_path),
                "title": title,
                "concepts": json.dumps(concepts[:10]),  # Store as JSON string
                "lecture_name": lecture_name,
                "course_folder": course_folder,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            # Create unique ID
            note_id = hashlib.md5(file_path.encode()).hexdigest()
            
            # Add to collection
            self.collections["knowledge_notes"].add(
                documents=[content],
                metadatas=[doc_metadata],
                ids=[note_id]
            )
            
            print(f"✅ Indexed knowledge note: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error indexing knowledge note {file_path}: {e}")
            return False
    
    def search(self, query: str, collection: str = "transcripts", limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content"""
        try:
            if collection not in self.collections:
                print(f"❌ Collection '{collection}' not found")
                return []
            
            results = self.collections[collection].query(
                query_texts=[query],
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                for i, doc in enumerate(documents):
                    result = {
                        "content": doc,
                        "distance": distances[i] if i < len(distances) else None,
                    }
                    # Add metadata if available
                    if i < len(metadatas) and metadatas[i]:
                        result.update(metadatas[i])
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def get_course_context(self, course_folder: str) -> Dict[str, Any]:
        """Get all content from a specific course for context analysis"""
        try:
            # Get transcripts from course
            transcript_results = self.collections["transcripts"].get(
                where={"course_folder": course_folder}
            )
            
            # Get notes from course  
            note_results = self.collections["knowledge_notes"].get(
                where={"course_folder": course_folder}
            )
            
            return {
                "course_folder": course_folder,
                "transcripts": {
                    "documents": transcript_results["documents"] or [],
                    "metadatas": transcript_results["metadatas"] or []
                },
                "notes": {
                    "documents": note_results["documents"] or [],
                    "metadatas": note_results["metadatas"] or []
                },
                "transcript_count": len(transcript_results["documents"] or []),
                "note_count": len(note_results["documents"] or [])
            }
            
        except Exception as e:
            print(f"❌ Error getting course context: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about indexed content"""
        try:
            transcript_count = self.collections["transcripts"].count()
            note_count = self.collections["knowledge_notes"].count()
            
            return {
                "transcripts": transcript_count,
                "knowledge_notes": note_count
            }
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {"transcripts": 0, "knowledge_notes": 0}
    
    def delete_all(self):
        """Delete all data (use with caution!)"""
        try:
            # Reset collections
            self.client.delete_collection("transcripts")
            self.client.delete_collection("knowledge_notes")
            
            # Recreate collections
            self.collections["transcripts"] = self.client.create_collection(
                name="transcripts",
                embedding_function=self.embedding_fn
            )
            
            self.collections["knowledge_notes"] = self.client.create_collection(
                name="knowledge_notes",
                embedding_function=self.embedding_fn
            )
            
            print("✅ Deleted all data from vector store")
            
        except Exception as e:
            print(f"❌ Error deleting data: {e}")


if __name__ == "__main__":
    # Test vector store
    vs = SimpleVectorStore()
    
    if vs.connect():
        stats = vs.get_stats()
        print(f"\nCurrent stats: {stats}")
        
        # Test search if we have data
        if stats["transcripts"] > 0:
            print("\nTesting search...")
            results = vs.search("machine learning", limit=2)
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['lecture_name']}: {result['content'][:100]}...")
    else:
        print("Failed to connect to ChromaDB!")