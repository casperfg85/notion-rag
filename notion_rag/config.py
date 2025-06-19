import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class Config:
    notion_token: str
    data_dir: Path
    openai_api_key: str = ""
    gemini_api_key: str = ""
    api_delay: float = 1.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    max_concurrent: int = 5
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "Config":
        # Load from YAML file first
        config_data: Dict[str, Any] = {}
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = Path("config.yaml")

        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}

        # Override with environment variables
        return cls(
            notion_token=os.getenv("NOTION_TOKEN", config_data.get("notion_token", "")),
            data_dir=Path(os.getenv("DATA_DIR", config_data.get("data_dir", "data"))),
            openai_api_key=os.getenv(
                "OPENAI_API_KEY", config_data.get("openai_api_key", "")
            ),
            gemini_api_key=os.getenv(
                "GEMINI_API_KEY", config_data.get("gemini_api_key", "")
            ),
            api_delay=float(os.getenv("API_DELAY", config_data.get("api_delay", 1.0))),
            max_retries=int(
                os.getenv("MAX_RETRIES", config_data.get("max_retries", 3))
            ),
            backoff_factor=float(
                os.getenv("BACKOFF_FACTOR", config_data.get("backoff_factor", 2.0))
            ),
            max_concurrent=int(
                os.getenv("MAX_CONCURRENT", config_data.get("max_concurrent", 5))
            ),
            log_level=os.getenv("LOG_LEVEL", config_data.get("log_level", "INFO")),
        )
