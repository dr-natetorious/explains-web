import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import faiss
from datetime import datetime

from doc_processor import DocumentChunk


class VectorStore:
    """Manages FAISS vector database for document search"""
    
    def __init__(self, index_path: str = "data/faiss_index", metadata_path: str = "data/metadata.json"):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.index_file = self.index_path / "index.faiss"
        self.chunks_file = self.index_path / "chunks.pkl"
        
        # Create directories if they don't exist
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load existing index
        self.index = None
        self.chunks = []  # List of DocumentChunk objects
        self.metadata = {}
        
        self.load_index()
    
    def load_index(self):
        """Load existing FAISS index and metadata"""
        try:
            if self.index_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                print(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                print("No existing index found, will create new one")
                
            if self.chunks_file.exists():
                with open(self.chunks_file, 'rb') as f:
                    self.chunks = pickle.load(f)
                print(f"Loaded {len(self.chunks)} document chunks")
            
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                print(f"Loaded metadata for {len(self.metadata.get('files', {}))} files")
            else:
                self.metadata = {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_chunks": 0,
                    "files": {},
                    "repos": {}
                }
                
        except Exception as e:
            print(f"Error loading index: {e}")
            self.index = None
            self.chunks = []
            self.metadata = {}
    
    def save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            if self.index is not None:
                faiss.write_index(self.index, str(self.index_file))
                print(f"Saved FAISS index with {self.index.ntotal} vectors")
            
            with open(self.chunks_file, 'wb') as f:
                pickle.dump(self.chunks, f)
            print(f"Saved {len(self.chunks)} document chunks")
            
            self.metadata["last_updated"] = datetime.now().isoformat()
            self.metadata["total_chunks"] = len(self.chunks)
            
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            print("Saved metadata")
            
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """Add new document chunks to the vector store"""
        if not chunks:
            return
        
        # Filter out chunks without embeddings
        valid_chunks = [chunk for chunk in chunks if chunk.embedding is not None]
        if not valid_chunks:
            print("No valid chunks with embeddings to add")
            return
        
        # Extract embeddings
        embeddings = np.array([chunk.embedding for chunk in valid_chunks])
        embedding_dim = embeddings.shape[1]
        
        # Initialize index if it doesn't exist
        if self.index is None:
            self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
            print(f"Created new FAISS index with dimension {embedding_dim}")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.index.add(embeddings)
        
        # Add chunks to our list
        self.chunks.extend(valid_chunks)
        
        # Update metadata
        for chunk in valid_chunks:
            file_key = f"{chunk.repo_name}/{chunk.source_file}"
            self.metadata["files"][file_key] = {
                "file_hash": chunk.file_hash,
                "processed_at": chunk.metadata.get("processed_at"),
                "chunk_count": self.metadata["files"].get(file_key, {}).get("chunk_count", 0) + 1
            }
            
            if chunk.repo_name not in self.metadata["repos"]:
                self.metadata["repos"][chunk.repo_name] = {
                    "files": [],
                    "total_chunks": 0
                }
            
            repo_files = self.metadata["repos"][chunk.repo_name]["files"]
            if chunk.source_file not in repo_files:
                repo_files.append(chunk.source_file)
            
            self.metadata["repos"][chunk.repo_name]["total_chunks"] += 1
        
        print(f"Added {len(valid_chunks)} chunks to vector store")
    
    def update_file(self, file_path: str, repo_name: str, new_chunks: List[DocumentChunk]):
        """Update chunks for a specific file (remove old, add new)"""
        file_key = f"{repo_name}/{file_path}"
        
        # Find existing chunks for this file
        chunks_to_keep = []
        removed_count = 0
        
        for chunk in self.chunks:
            if chunk.source_file == file_path and chunk.repo_name == repo_name:
                removed_count += 1
                continue  # Skip this chunk (remove it)
            chunks_to_keep.append(chunk)
        
        if removed_count > 0:
            print(f"Removing {removed_count} old chunks for {file_key}")
            self.chunks = chunks_to_keep
            
            # Only rebuild if we have chunks remaining, otherwise add will create new index
            if self.chunks:
                self._rebuild_index()
            else:
                self.index = None
        
        # Add new chunks
        self.add_chunks(new_chunks)
        
        print(f"Updated {file_key} with {len(new_chunks)} new chunks")
    
    def _rebuild_index(self):
        """Rebuild the FAISS index from current chunks"""
        if not self.chunks:
            self.index = None
            return
        
        embeddings = np.array([chunk.embedding for chunk in self.chunks if chunk.embedding is not None])
        if len(embeddings) == 0:
            self.index = None
            return
        
        embedding_dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(embedding_dim)
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        print(f"Rebuilt index with {len(embeddings)} vectors")
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar document chunks"""
        if self.index is None or len(self.chunks) == 0:
            return []
        
        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, min(k, len(self.chunks)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):  # Valid index
                results.append((self.chunks[idx], float(score)))
        
        return results
    
    def get_file_status(self, file_path: str, repo_name: str, current_hash: str) -> str:
        """Check if file needs to be processed (new, updated, or unchanged)"""
        file_key = f"{repo_name}/{file_path}"
        
        if file_key not in self.metadata["files"]:
            return "new"
        
        stored_hash = self.metadata["files"][file_key].get("file_hash", "")
        if stored_hash != current_hash:
            return "updated"
        
        return "unchanged"
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        stats = {
            "total_chunks": len(self.chunks),
            "total_files": len(self.metadata.get("files", {})),
            "total_repos": len(self.metadata.get("repos", {})),
            "index_size": self.index.ntotal if self.index else 0,
            "last_updated": self.metadata.get("last_updated"),
            "repos": {}
        }
        
        for repo_name, repo_data in self.metadata.get("repos", {}).items():
            stats["repos"][repo_name] = {
                "files": len(repo_data.get("files", [])),
                "chunks": repo_data.get("total_chunks", 0)
            }
        
        return stats
    
    def cleanup_temp_files(self):
        """Remove temporary downloaded files"""
        temp_dir = Path("temp_downloads")
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            print("Cleaned up temporary files")


# Example usage
if __name__ == "__main__":
    from sentence_transformers import SentenceTransformer
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Example: Add some chunks (normally these would come from DocumentProcessor)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Print current stats
    stats = vector_store.get_stats()
    print("Vector store stats:", json.dumps(stats, indent=2))
    
    # Example search
    if vector_store.index is not None:
        query = "machine learning algorithms"
        query_embedding = model.encode(query)
        results = vector_store.search(query_embedding, k=3)
        
        print(f"\nSearch results for '{query}':")
        for chunk, score in results:
            print(f"Score: {score:.4f}")
            print(f"Source: {chunk.repo_name}/{chunk.source_file}")
            print(f"Content: {chunk.content[:200]}...")
            print("-" * 50)