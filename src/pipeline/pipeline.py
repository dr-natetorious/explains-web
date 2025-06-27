#!/usr/bin/env python3
"""
Main pipeline script for processing documents and updating vector database.
This script is called by the GitHub Action workflow.
"""

import os
import sys
import argparse
import yaml
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add current directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.doc_processor import DocumentProcessor
from src.vector_store import VectorStore


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pipeline.log')
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        # Return default configuration if file doesn't exist
        return {
            'repositories': [
                {
                    'name': 'example-repo',
                    'url': 'https://github.com/username/example-repo',
                    'file_types': ['.pdf', '.docx', '.md'],
                    'enabled': True
                }
            ],
            'settings': {
                'model_name': 'all-MiniLM-L6-v2',
                'chunk_size': 512,
                'overlap': 50,
                'file_types': ['.pdf', '.docx', '.doc', '.md', '.markdown']
            }
        }


def should_process_repo(repo_config: Dict, target_repos: List[str]) -> bool:
    """Check if a repository should be processed"""
    if not repo_config.get('enabled', True):
        return False
    
    if target_repos:
        repo_name = repo_config.get('name', '')
        return repo_name in target_repos
    
    return True


async def process_repository(repo_config: Dict, processor: DocumentProcessor, 
                      vector_store: VectorStore, force_rebuild: bool = False,
                      github_token: str = None) -> Dict:
    """Process a single repository asynchronously"""
    logger = logging.getLogger(__name__)
    
    repo_name = repo_config['name']
    repo_url = repo_config['url']
    file_types = repo_config.get('file_types', ['.pdf', '.docx', '.md'])
    
    logger.info(f"Processing repository: {repo_name}")
    
    results = {
        'repo_name': repo_name,
        'files_processed': 0,
        'chunks_added': 0,
        'files_updated': 0,
        'files_skipped': 0,
        'errors': []
    }
    
    try:
        if force_rebuild:
            # Process entire repository at once
            chunks = await processor.process_repository_async(
                repo_url, repo_name, file_types, github_token
            )
            
            if chunks:
                vector_store.add_chunks(chunks)
                results['files_processed'] = len(set(chunk.source_file for chunk in chunks))
                results['chunks_added'] = len(chunks)
                logger.info(f"Added {len(chunks)} chunks from {repo_name}")
        else:
            # Check individual files for changes (slower but more efficient for updates)
            files = await processor.get_repo_files_async(repo_url, file_types, github_token)
            logger.info(f"Found {len(files)} files in {repo_name}")
            
            # Process files in smaller batches for change detection
            batch_size = 10
            for i in range(0, len(files), batch_size):
                batch_files = files[i:i + batch_size]
                
                # Download batch and check for changes
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    download_tasks = [
                        processor.download_file_from_github_async(session, repo_url, file_path, github_token)
                        for file_path in batch_files
                    ]
                    local_files = await asyncio.gather(*download_tasks, return_exceptions=True)
                
                # Process each file if it changed
                processing_tasks = []
                for local_file, file_path in zip(local_files, batch_files):
                    if isinstance(local_file, str) and local_file:
                        try:
                            current_hash = processor.get_file_hash(local_file)
                            file_status = vector_store.get_file_status(file_path, repo_name, current_hash)
                            
                            if file_status == "unchanged":
                                logger.info(f"Skipping unchanged file: {file_path}")
                                results['files_skipped'] += 1
                                continue
                            
                            # Process asynchronously
                            processing_tasks.append(
                                processor.process_file_async(local_file, repo_name)
                            )
                        except Exception as e:
                            results['errors'].append(f"Error checking {file_path}: {str(e)}")
                
                # Wait for processing tasks
                if processing_tasks:
                    batch_chunks = await asyncio.gather(*processing_tasks, return_exceptions=True)
                    
                    for chunks, file_path in zip(batch_chunks, batch_files):
                        if isinstance(chunks, list) and chunks:
                            vector_store.add_chunks(chunks)
                            results['files_processed'] += 1
                            results['chunks_added'] += len(chunks)
                            logger.info(f"Added {len(chunks)} chunks from {file_path}")
                        elif isinstance(chunks, Exception):
                            results['errors'].append(f"Error processing {file_path}: {str(chunks)}")
    
    except Exception as e:
        error_msg = f"Error processing repository {repo_name}: {str(e)}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
    
    return results


async def main_async():
    """Async main pipeline function"""
    parser = argparse.ArgumentParser(description='Update vector database from GitHub repositories')
    parser.add_argument('--config', default='config/repos_to_index.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--force-rebuild', action='store_true',
                       help='Force complete rebuild of vector database')
    parser.add_argument('--target-repos', default='',
                       help='Comma-separated list of repository names to process')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Maximum number of worker threads for processing')
    parser.add_argument('--max-concurrent-repos', type=int, default=3,
                       help='Maximum number of repositories to process concurrently')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    logger.info("Starting async vector database update pipeline")
    
    # Parse target repos
    target_repos = [repo.strip() for repo in args.target_repos.split(',') if repo.strip()]
    if target_repos:
        logger.info(f"Target repositories: {target_repos}")
    
    # Load configuration
    config = load_config(args.config)
    logger.info(f"Loaded configuration for {len(config['repositories'])} repositories")
    
    # Initialize components
    settings = config.get('settings', {})
    processor = DocumentProcessor(
        model_name=settings.get('model_name', 'all-MiniLM-L6-v2'),
        max_workers=args.max_workers
    )
    vector_store = VectorStore()
    
    # Get GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.warning("No GitHub token found, rate limits may apply")
    
    # Filter repositories to process
    repos_to_process = [
        repo for repo in config['repositories']
        if should_process_repo(repo, target_repos)
    ]
    
    if not repos_to_process:
        logger.warning("No repositories to process")
        return
    
    # Process repositories concurrently (in batches)
    total_results = {
        'repositories_processed': 0,
        'total_files_processed': 0,
        'total_chunks_added': 0,
        'total_files_updated': 0,
        'total_files_skipped': 0,
        'total_errors': 0,
        'repo_results': []
    }
    
    # Process repos in batches to control resource usage
    batch_size = args.max_concurrent_repos
    for i in range(0, len(repos_to_process), batch_size):
        batch_repos = repos_to_process[i:i + batch_size]
        logger.info(f"Processing repository batch {i//batch_size + 1}/{(len(repos_to_process) + batch_size - 1)//batch_size}")
        
        # Process batch concurrently
        batch_tasks = [
            process_repository(repo_config, processor, vector_store, args.force_rebuild, github_token)
            for repo_config in batch_repos
        ]
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Aggregate results
        for result in batch_results:
            if isinstance(result, dict):
                total_results['repositories_processed'] += 1
                total_results['total_files_processed'] += result['files_processed']
                total_results['total_chunks_added'] += result['chunks_added']
                total_results['total_files_updated'] += result['files_updated']
                total_results['total_files_skipped'] += result['files_skipped']
                total_results['total_errors'] += len(result['errors'])
                total_results['repo_results'].append(result)
            elif isinstance(result, Exception):
                logger.error(f"Repository processing failed: {result}")
                total_results['total_errors'] += 1
    
    # Clean up
    processor.executor.shutdown(wait=True)
    
    # Save updated vector store
    logger.info("Saving vector database...")
    vector_store.save_index()
    
    # Clean up temporary files
    vector_store.cleanup_temp_files()
    
    # Print summary
    logger.info("Pipeline completed!")
    logger.info(f"Repositories processed: {total_results['repositories_processed']}")
    logger.info(f"Files processed: {total_results['total_files_processed']}")
    logger.info(f"Files updated: {total_results['total_files_updated']}")
    logger.info(f"Files skipped: {total_results['total_files_skipped']}")
    logger.info(f"Chunks added: {total_results['total_chunks_added']}")
    logger.info(f"Total errors: {total_results['total_errors']}")
    
    # Save detailed results
    with open('pipeline_results.json', 'w') as f:
        json.dump(total_results, f, indent=2)
    
    # Exit with error code if there were errors
    if total_results['total_errors'] > 0:
        logger.error("Pipeline completed with errors")
        sys.exit(1)
    else:
        logger.info("Pipeline completed successfully")


def main():
    """Synchronous entry point that runs async main"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()