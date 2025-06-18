#!/usr/bin/env python3
'''
Notion RAG system with agno agent using gemini-flash-2.5
Prerequisites:
- Run scripts/pull.py to fetch Notion data
- Run scripts/parse.py to parse the data
- Run scripts/index.py to create the vector database
- Set GOOGLE_API_KEY environment variable
'''

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config
from db.query import search_pages, get_table_stats

from agno import Agent, tool
from agno.models.litellm import LiteLLM


@tool
def search_notion_pages(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    '''
    Search through Notion pages for relevant content.
    
    Args:
        query: The search query to find relevant pages
        limit: Maximum number of results to return (default: 5)
        
    Returns:
        List of relevant pages with their content, titles, and URLs
    '''
    results = search_pages(query, limit=limit)
    
    # Format results for the agent
    formatted_results = []
    for result in results:
        formatted_results.append({
            'title': result.get('title', 'No title'),
            'url': result.get('url', 'No URL'),
            'content': result.get('text', ''),
            'created_time': result.get('created_time'),
            'last_edited_time': result.get('last_edited_time')
        })
    
    return formatted_results


def create_notion_agent(model_name: str) -> Agent:
    '''Create a simple Notion RAG agent with gemini-flash-2.5'''
    return Agent(
        model=LiteLLM(model=model_name),
        tools=[search_notion_pages],
        instructions='''You are a helpful assistant that can search through Notion pages to answer questions.
            When a user asks a question:
            1. Use the search_notion_pages tool to find relevant content
            2. Analyze the search results to provide a comprehensive answer
            3. Always cite the source pages by mentioning their titles and URLs
            4. If no relevant information is found, say so clearly
            5. Be concise but thorough in your responses''',
        show_tool_calls=True,
        markdown=True
    )


def main():
    '''Test the Notion RAG system with agno agent'''
    # Check if database exists
    stats = get_table_stats()
    model = 'gemini/gemini-2.5-flash-preview-05-20'
    if not stats.get('exists'):
        print('Vector database not found. Please run scripts/index.py first.')
        return
    
    print(f'=== Notion RAG Agent ===')
    print(f'Database: {stats["total_pages"]} pages indexed')
    print(f'Model: {model}')
    print('Type your questions or \'quit\' to exit\n')
    
    # Create the agent
    agent = create_notion_agent(model)
    
    while True:
        try:
            user_input = input('Question: ').strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if not user_input:
                continue
            
            print('\n' + '='*50)
            agent.print_response(user_input)
            print('='*50 + '\n')
                
        except KeyboardInterrupt:
            print('\nExiting...')
            break
        except Exception as e:
            print(f'Error: {e}')


if __name__ == '__main__':
    main()