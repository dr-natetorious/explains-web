import os
import hashlib
import json
import re
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import PyPDF2
import docx
import markdown
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document"""
    content: str
    source_file: str
    repo_name: str
    chunk_id: str
    file_hash: str
    metadata: Dict
    embedding: Optional[np.ndarray] = None


class DocumentProcessor:
    """Processes documents from GitHub repos and creates vector embeddings"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", max_workers: int = 4):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = 100  # approximate words
        self.overlap = 10  # approximate words
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF {file_path}: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting DOCX {file_path}: {e}")
            return ""
    
    def extract_text_from_md(self, file_path: str) -> str:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            # Convert markdown to plain text
            html = markdown.markdown(md_content)
            # Simple HTML tag removal
            text = re.sub('<[^<]+?>', '', html)
            return text.strip()
        except Exception as e:
            print(f"Error extracting MD {file_path}: {e}")
            return ""
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return ""
    
    def chunk_text(self, text: str, file_path: str, repo_name: str) -> List[DocumentChunk]:
        """Split text into overlapping chunks"""
        if not text.strip():
            return []
        
        # Simple sentence-based chunking
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        file_hash = self.get_file_hash(file_path)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if adding this sentence would exceed chunk size (approximate word count)
            approx_words = len(current_chunk.split()) + len(sentence.split())
            if approx_words > self.chunk_size and current_chunk:
                # Create chunk
                chunk_id = f"{repo_name}_{Path(file_path).stem}_{len(chunks)}"
                chunk = DocumentChunk(
                    content=current_chunk.strip(),
                    source_file=file_path,
                    repo_name=repo_name,
                    chunk_id=chunk_id,
                    file_hash=file_hash,
                    metadata={
                        "file_type": Path(file_path).suffix,
                        "chunk_index": len(chunks),
                        "processed_at": datetime.now().isoformat()
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = sentences[max(0, i-2):i]
                current_chunk = " ".join(overlap_sentences) + " " + sentence
            else:
                current_chunk += " " + sentence
        
        # Add final chunk if it has content
        if current_chunk.strip():
            chunk_id = f"{repo_name}_{Path(file_path).stem}_{len(chunks)}"
            chunk = DocumentChunk(
                content=current_chunk.strip(),
                source_file=file_path,
                repo_name=repo_name,
                chunk_id=chunk_id,
                file_hash=file_hash,
                metadata={
                    "file_type": Path(file_path).suffix,
                    "chunk_index": len(chunks),
                    "processed_at": datetime.now().isoformat()
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def process_file(self, file_path: str, repo_name: str) -> List[DocumentChunk]:
        """Process a single file and return document chunks"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            text = self.extract_text_from_docx(file_path)
        elif file_ext in ['.md', '.markdown']:
            text = self.extract_text_from_md(file_path)
        else:
            print(f"Unsupported file type: {file_ext}")
            return []
        
        if not text:
            print(f"No text extracted from {file_path}")
            return []
        
        chunks = self.chunk_text(text, file_path, repo_name)
        
        # Generate embeddings for chunks
        for chunk in chunks:
            try:
                embedding = self.model.encode(chunk.content)
                chunk.embedding = embedding
            except Exception as e:
                print(f"Error generating embedding for {chunk.chunk_id}: {e}")
        
        return chunks
    
    def download_file_from_github(self, repo_url: str, file_path: str, token: str = None) -> str:
        """Download a file from GitHub and return local path"""
        # Convert GitHub URL to raw content URL
        if repo_url.startswith('https://github.com/'):
            repo_path = repo_url.replace('https://github.com/', '')
            # Try main first, fallback to master
            for branch in ['main', 'master']:
                raw_url = f"https://raw.githubusercontent.com/{repo_path}/{branch}/{file_path}"
                headers = {}
                if token:
                    headers['Authorization'] = f'token {token}'
                
                try:
                    response = requests.get(raw_url, headers=headers)
                    if response.status_code == 200:
                        # Create local file path
                        local_dir = Path("temp_downloads") / repo_path.replace('/', '_')
                        local_dir.mkdir(parents=True, exist_ok=True)
                        local_file = local_dir / Path(file_path).name
                        
                        with open(local_file, 'wb') as f:
                            f.write(response.content)
                        
                        return str(local_file)
                except Exception as e:
                    print(f"Error downloading from branch {branch}: {e}")
                    continue
        
        print(f"Error downloading {file_path} from {repo_url}")
        return None
    
    def get_repo_files(self, repo_url: str, file_types: List[str] = None, token: str = None) -> List[str]:
        """Get list of files from GitHub repo"""
        if file_types is None:
            file_types = ['.pdf', '.docx', '.doc', '.md', '.markdown']
        
        # Convert to API URL
        if repo_url.startswith('https://github.com/'):
            repo_path = repo_url.replace('https://github.com/', '')
            # Try main first, fallback to master
            for branch in ['main', 'master']:
                api_url = f"https://api.github.com/repos/{repo_path}/git/trees/{branch}?recursive=1"
                headers = {}
                if token:
                    headers['Authorization'] = f'token {token}'
                
                try:
                    response = requests.get(api_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        files = []
                        for item in data.get('tree', []):
                            if item['type'] == 'blob':  # It's a file
                                file_path = item['path']
                                if any(file_path.lower().endswith(ft) for ft in file_types):
                                    files.append(file_path)
                        return files
                except Exception as e:
                    print(f"Error trying branch {branch}: {e}")
                    continue
            return []
        else:
            return []


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        processor = DocumentProcessor(max_workers=4)
        
        # Example: Process files from GitHub repo asynchronously
        repo_url = "https://github.com/username/repo"
        token = "your_github_token"  # Optional
        
        all_chunks = await processor.process_repository_async(
            repo_url, 
            "my-repo", 
            token=token,
            max_concurrent_downloads=5
        )
        
        print(f"Generated {len(all_chunks)} document chunks")
        
        # Clean up
        processor.executor.shutdown(wait=True)
    
    asyncio.run(main())