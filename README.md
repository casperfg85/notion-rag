# Notion RAG

A Retrieval-Augmented Generation (RAG) system built on top of Notion, using LanceDB for vector storage and LiteLLM for embeddings and chat completion.

## Features

- **Notion API Integration**: Fetch pages, blocks, and databases from your Notion workspace
- **Vector Search**: Create embeddings and perform semantic search using LanceDB
- **Multiple Embedding Providers**: Support for OpenAI and Google via LiteLLM
- **Resumable Data Pulls**: Stateful pulling with error recovery
- **Structured Parsing**: Convert Notion content to clean, searchable format
- **RAG Chat Interface**: Interactive chat with your Notion content
- **Entity Isolation**: Process multiple Notion trees with complete data isolation

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd notion-rag

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `config.yaml` file:

```yaml
notion_token: "your_notion_integration_token"
data_dir: "data"
log_level: "INFO"
```

Set environment variables:

```bash
export NOTION_TOKEN="your_notion_integration_token"

# For embeddings (choose one):
export OPENAI_API_KEY="your_openai_api_key"
# OR
export GOOGLE_API_KEY="your_google_api_key"
```

### 3. Run the Pipeline

```bash
# Step 1: Pull data from Notion for a specific entity
python scripts/pull.py --root_entity_id <NOTION_PAGE_ID>

# Step 2: Parse the data into a flat structure
python scripts/parse.py --root_entity_id <NOTION_PAGE_ID>

# Step 3: Create vector embeddings and database
python scripts/index.py --root_entity_id <NOTION_PAGE_ID>

# Step 4: Test the RAG system
python test_rag.py --root_entity_id <NOTION_PAGE_ID>
```

## Pipeline Overview

The system consists of three main stages:

1. **Pull**: Fetch data from Notion API and store as JSON files
2. **Parse**: Convert Notion data into a flat, searchable format
3. **Index**: Create vector embeddings and LanceDB database

### Data Flow

```
Notion API → Raw JSON Files → Parsed JSON → Vector Database → RAG Search
```

### Entity Isolation

Each root entity ID gets its own isolated data structure:

```
data/
├── <entity_id_1>/
│   ├── raw/               # Raw JSON files from Notion API
│   │   └── pull_state.json # Resumable pull state
│   └── parsed/            # Processed data files
│       └── parsed_pages.json
├── <entity_id_2>/
│   ├── raw/
│   └── parsed/
└── databases/
    ├── <entity_id_1>.lancedb # Isolated vector database
    └── <entity_id_2>.lancedb
```

## Project Structure

```
notion-rag/
├── src/
│   ├── api/           # Notion API client and data models
│   ├── parsing/       # Data parsing and transformation
│   ├── db/           # Vector database operations
│   └── utils/        # Logging, persistence utilities
├── scripts/
│   ├── pull.py       # Fetch data from Notion
│   ├── parse.py      # Parse raw data
│   └── index.py      # Create vector index
├── data/             # Default data directory
│   ├── <entity_id>/  # Entity-specific data directories
│   └── databases/    # Vector databases
├── config.yaml       # Configuration file
├── test_rag.py       # RAG system test interface
└── requirements.txt
```

## Configuration Options

### config.yaml

```yaml
# Required
notion_token: "secret_xxx"           # Notion integration token
data_dir: "data"                     # Directory for all data storage

# Optional
api_delay: 1.0                       # Delay between API calls (seconds)
max_retries: 3                       # Max retries for failed API calls
backoff_factor: 2.0                  # Exponential backoff multiplier
max_concurrent: 5                    # Max concurrent API requests
log_level: "INFO"                    # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Environment Variables

All config.yaml values can be overridden with environment variables:

- `NOTION_TOKEN`
- `DATA_DIR`
- `API_DELAY`
- `MAX_RETRIES`
- `BACKOFF_FACTOR`
- `MAX_CONCURRENT`
- `LOG_LEVEL`

## Script Usage

### Pull Script

```bash
# Pull data for a specific entity
python scripts/pull.py --root_entity_id <ENTITY_ID>

# Reset state and start fresh
python scripts/pull.py --root_entity_id <ENTITY_ID> --reset

# Retry only failed entities
python scripts/pull.py --root_entity_id <ENTITY_ID> --retry-failed
```

### Parse Script

```bash
# Parse data for a specific entity
python scripts/parse.py --root_entity_id <ENTITY_ID>
```

### Index Script

```bash
# Create vector index for a specific entity
python scripts/index.py --root_entity_id <ENTITY_ID>
```

## Advanced Usage

### Resumable Pulls

The pull process is resumable per entity - if it fails partway through, you can run it again and it will continue from where it left off:

```bash
# If pull fails, just run again
python scripts/pull.py --root_entity_id <ENTITY_ID>

# Reset state to start fresh
python scripts/pull.py --root_entity_id <ENTITY_ID> --reset
```

### Multiple Entities

Process multiple Notion trees independently:

```bash
# Process first entity
python scripts/pull.py --root_entity_id entity1
python scripts/parse.py --root_entity_id entity1
python scripts/index.py --root_entity_id entity1

# Process second entity (completely isolated)
python scripts/pull.py --root_entity_id entity2
python scripts/parse.py --root_entity_id entity2
python scripts/index.py --root_entity_id entity2
```

### Custom Data Directory

```bash
export DATA_DIR="/path/to/custom/data"
python scripts/pull.py --root_entity_id <ENTITY_ID>
```

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL="DEBUG"
python scripts/pull.py --root_entity_id <ENTITY_ID>
```

## API Integration

### Setting up Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name and select your workspace
4. Copy the "Internal Integration Token"
5. Share your root page with the integration

### Finding Page IDs

Page IDs can be found in the URL:
```
https://notion.so/workspace/Page-Title-32-character-page-id
```

## Database Structure

Each entity gets its own isolated database with a unique table name:

- Database path: `{data_dir}/databases/{entity_id}.lancedb`
- Table name: `notion_content_{entity_id}`

This ensures complete isolation between different Notion trees.

## Troubleshooting

### Common Issues

1. **"Notion API returned 401"**: Check your integration token and page permissions
2. **"No embedding API key found"**: Set either `OPENAI_API_KEY` or `GOOGLE_API_KEY`
3. **"Raw data not found"**: Run `python scripts/pull.py --root_entity_id <ID>` first
4. **"Parsed data not found"**: Run `python scripts/parse.py --root_entity_id <ID>` after pulling

### Getting Help

Check the logs for detailed error messages:

```bash
export LOG_LEVEL="DEBUG"
python scripts/pull.py --root_entity_id <ENTITY_ID>
```

## TODO
- Remove relative imports
- Multi-modal search
