import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Config:
    notion_token: str
    data_dir: Path
    main_page_id: str
    api_delay: float = 1.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    max_concurrent: int = 5
    log_level: str = 'INFO'
    
    @classmethod
    def load(cls, config_file: Optional[str] = None) -> 'Config':
        # Load from YAML file first
        config_data = {}
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = Path('config.yaml')
            
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
        
        # Override with environment variables
        return cls(
            notion_token=os.getenv('NOTION_TOKEN', config_data.get('notion_token', '')),
            data_dir=Path(os.getenv('DATA_DIR', config_data.get('data_dir', 'data'))),
            main_page_id=os.getenv('MAIN_PAGE_ID', config_data.get('main_page_id', '')),
            api_delay=float(os.getenv('API_DELAY', config_data.get('api_delay', 1.0))),
            max_retries=int(os.getenv('MAX_RETRIES', config_data.get('max_retries', 3))),
            backoff_factor=float(os.getenv('BACKOFF_FACTOR', config_data.get('backoff_factor', 2.0))),
            max_concurrent=int(os.getenv('MAX_CONCURRENT', config_data.get('max_concurrent', 5))),
            log_level=os.getenv('LOG_LEVEL', config_data.get('log_level', 'INFO'))
        )