#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from api.puller import NotionPuller, EntityType


def main():
    parser = argparse.ArgumentParser(description='Pull content from Notion')
    parser.add_argument('--root_entity_id', required=True, help='Root entity ID to pull from Notion')
    parser.add_argument('--reset', action='store_true', help='Reset pull state and start fresh')
    parser.add_argument('--retry-failed', action='store_true', help='Retry only previously failed entities')
    args = parser.parse_args()
    
    # Load configuration
    config = Config.load()
    
    if not config.notion_token:
        print('Error: NOTION_TOKEN not set')
        sys.exit(1)
    
    # Create entity-specific directories
    entity_data_dir = config.data_dir / args.root_entity_id
    raw_dir = entity_data_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Create puller with entity-specific paths
    puller = NotionPuller(config, entity_data_dir)
    
    # Handle reset and retry options
    if args.reset:
        puller.reset_state()
        print('Pull state reset. Starting fresh pull...')
    elif args.retry_failed:
        summary = puller.get_pull_summary()
        if summary['failed_entities'] > 0:
            print(f'Retrying {summary["failed_entities"]} failed entities...')
            puller.pull_failed_entities_only()
            
            # Print final summary
            final_summary = puller.get_pull_summary()
            print(f'Retry completed:')
            print(f'  - Completed entities: {final_summary["completed_entities"]}')
            print(f'  - Failed entities: {final_summary["failed_entities"]}')
            
            if final_summary['failed_details']:
                print('Failed entities:')
                for entity_id, error in final_summary['failed_details'].items():
                    print(f'  - {entity_id}: {error}')
            return
        else:
            print('No failed entities to retry.')
            return
    
    try:
        print(f'Pulling content for entity {args.root_entity_id}...')
        print(f'Output will be saved to: {raw_dir}')
        puller.pull_all(args.root_entity_id, EntityType.BLOCK)
        
        # Print summary
        summary = puller.get_pull_summary()
        print(f'Pull completed:')
        print(f'  - Completed entities: {summary["completed_entities"]}')
        print(f'  - Failed entities: {summary["failed_entities"]}')
        print(f'  - Data saved to: {raw_dir}')
        
        if summary['failed_details']:
            print('Failed entities:')
            for entity_id, error in summary['failed_details'].items():
                print(f'  - {entity_id}: {error}')
                
    except KeyboardInterrupt:
        print('Pull interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'Pull failed: {e}')
        raise(e)
        sys.exit(1)


if __name__ == '__main__':
    main()