#!/usr/bin/env python3

import warnings
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.models.litellm import LiteLLM
from agno.team.team import Team
from agno.tools import tool

from notion_rag.config import Config
from notion_rag.db.engine import DBEngine

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

"""
Notion RAG system with agno agent using gemini-flash-2.5
Prerequisites:
- Run scripts/pull.py to fetch Notion data
- Run scripts/parse.py to parse the data
- Run scripts/index.py to create the vector database
- Set GEMINI_API_KEY environment variable
"""


def create_notion_agent(
    db_engine: DBEngine,
    model_id: str,
    name: str,
    instructions: Optional[List[str]] = None,
    role: Optional[List[str]] = None,
    tools: Optional[List[Any]] = None,
) -> Agent:
    """Create a simple Notion RAG agent with gemini-flash-2.5"""

    @tool
    def search_notion_pages(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search through Notion pages for relevant content.

        Args:
            query: The search query to find relevant pages
            limit: Maximum number of results to return (default: 5)

        Returns:
            List of relevant pages with their content, titles, and URLs
        """
        results = db_engine.search_pages(query, limit=limit)
        # Format results for the agent
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "title": result.get("title", "No title"),
                    "url": result.get("url", "No URL"),
                    "content": result.get("text", ""),
                    "created_time": result.get("created_time"),
                    "last_edited_time": result.get("last_edited_time"),
                }
            )

        return formatted_results

    default_instructions = [
        "You are a helpful assistant that can search through Notion pages to answer questions",
        "When a user asks a question:",
        "1. Use the search_notion_pages tool to find relevant content",
        "2. Analyze the search results to provide a comprehensive answer",
        "3. Always cite the source pages by mentioning their titles and URLs",
        "4. Compile all the relevant links at the end of your response",
        "5. If no relevant information is found, say so clearly",
        "6. Be concise but thorough in your responses",
    ]

    default_role = [
        "You are a Notion workspace expert assistant",
        "Your expertise lies in:",
        "1. Finding and explaining information from the user's Notion pages",
        "2. Providing accurate, well-cited answers",
        "3. Maintaining a helpful and professional tone",
    ]

    agent_tools = [search_notion_pages]
    if tools:
        agent_tools.extend(tools)

    return Agent(
        model=LiteLLM(id=model_id),
        tools=agent_tools,
        instructions=instructions or default_instructions,
        role=role or default_role,
        show_tool_calls=True,
        markdown=True,
        add_datetime_to_instructions=True,
    )


def main():
    """Test the Notion RAG system with agno agent"""
    model = "gemini/gemini-2.5-flash"
    notion_db_id = ""
    config = Config.load()

    # Create entity-specific database path
    db_dir = config.data_dir / "databases"
    notion_db = DBEngine(config, db_path=db_dir / f"{notion_db_id}.lancedb")

    print("=== Notion RAG Agent ===")
    print(f'Database: {notion_db.get_table_stats()["total_pages"]} pages indexed')

    print(f"Model: {model}")
    print("Type your questions or 'quit' to exit\n")

    # Create the agent
    notion_db_agent = create_notion_agent(
        db_engine=notion_db, model_id=model, name="notion_agent"
    )

    agentic_team = Team(
        name="Agent Team",
        mode="coordinate",
        model=LiteLLM(id=model),
        members=[notion_db_agent],
        show_tool_calls=True,
        markdown=True,
        description="You are a team of experts with deep domain context",
        instructions=[
            "Coordinate between team members to provide comprehensive answers",
            "Leverage each member's expertise for their specific domain",
            "Combine insights from different documentation sources when relevant",
            "Ensure all responses are well-cited and accurate",
            "Maintain a consistent, professional tone across all responses",
        ],
        enable_agentic_context=True,
        show_members_responses=True,
    )

    while True:
        try:
            user_input = input("Question: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            if not user_input:
                continue

            print("\n" + "=" * 50)
            agentic_team.print_response(user_input)
            print("=" * 50 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
