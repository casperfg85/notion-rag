#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from db.indexer import NotionIndexer


def main():
    """Create vector index from parsed Notion data"""
    parser = argparse.ArgumentParser(description='Create vector index from parsed Notion data')
    parser.add_argument('--root_entity_id', required=True, help='Root entity ID to create index for')
    args = parser.parse_args()
    
    # Load configuration
    config = Config.load()
    
    # Create entity-specific directories
    entity_data_dir = config.data_dir / args.root_entity_id
    parsed_dir = entity_data_dir / 'parsed'
    parsed_file = parsed_dir / 'parsed_pages.json'
    
    # Check if parsed data exists
    if not parsed_file.exists():
        print(f'Error: Parsed data not found at {parsed_file}. Run scripts/parse.py --root_entity_id {args.root_entity_id} first.')
        sys.exit(1)
    
    # Check for API keys
    import os
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
        print('Error: Please set either OPENAI_API_KEY or GOOGLE_API_KEY environment variable')
        sys.exit(1)
    
    # Create entity-specific database path under data_dir
    db_dir = config.data_dir / 'databases'
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / f'{args.root_entity_id}.lancedb'
    
    # Create indexer with entity-specific paths
    indexer = NotionIndexer(config, entity_data_dir, db_path, args.root_entity_id)
    
    try:
        print(f'Starting indexing operation for entity {args.root_entity_id}...')
        print(f'Reading from: {parsed_file}')
        print(f'Database will be created at: {db_path}')
        
        # Ask if user wants to recreate index
        recreate = False
        if indexer.get_table() is not None:
            response = input('Vector index already exists. Recreate? (y/n): ').strip().lower()
            recreate = response == 'y'
        
        stats = indexer.create_index(recreate=recreate)
        
        print(f'Indexing completed successfully:')
        print(f'  - Indexed documents: {stats["indexed_documents"]}')
        print(f'  - Table name: {stats["table_name"]}')
        print(f'  - Embedding model: {stats["embedding_model"]}')
        print(f'  - Database location: {db_path}')
        
    except KeyboardInterrupt:
        print('Indexing interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'Indexing failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()