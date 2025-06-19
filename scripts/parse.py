#!/usr/bin/env python3

import argparse
import sys
import uuid


from notion_rag.config import Config
from notion_rag.parsing.orchestrator import ParseOrchestrator


def main():
    """Parse Notion API data into flat format for RAG"""
    parser = argparse.ArgumentParser(
        description="Parse Notion API data into flat format for RAG"
    )
    parser.add_argument(
        "--root_entity_id", required=True, help="Root entity ID to use for the database"
    )
    args = parser.parse_args()

    # Validate entity ID format
    try:
        uuid.UUID(args.root_entity_id)
    except ValueError:
        print(
            f"Error: Invalid entity ID format. Expected UUID, got: {args.root_entity_id}"
        )
        sys.exit(1)

    # Load configuration
    config = Config.load()

    # Create entity-specific directories
    entity_data_dir = config.data_dir / args.root_entity_id
    raw_dir = entity_data_dir / "raw"
    parsed_dir = entity_data_dir / "parsed"

    # Check if raw data exists
    if not raw_dir.exists():
        print(
            f"Error: Raw data directory not found at {raw_dir}. Run scripts/pull.py --root_entity_id {args.root_entity_id} first."
        )
        sys.exit(1)

    # Create parsed directory
    parsed_dir.mkdir(parents=True, exist_ok=True)

    # Create orchestrator with entity-specific paths
    orchestrator = ParseOrchestrator(config, entity_data_dir)

    try:
        print(f"Starting parsing operation for entity {args.root_entity_id}...")
        print(f"Reading from: {raw_dir}")
        print(f"Writing to: {parsed_dir}")
        result = orchestrator.parse_all()

        print("Parsing completed successfully:")
        print(f'  - Total entities processed: {len(result["flat_entities"])}')
        print(f'  - Pages created: {len(result["pages"])}')
        print(f"  - Output saved to: {parsed_dir}")

    except KeyboardInterrupt:
        print("Parsing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Parsing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
