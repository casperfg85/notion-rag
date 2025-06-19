import json
from pathlib import Path
from typing import Any, Dict, Set


class PullState:
    """Manages state for resumable pulls"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.completed_entities: Set[str] = set()
        self.failed_entities: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.load_state()

    def load_state(self):
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.completed_entities = set(data.get("completed", []))
                    self.failed_entities = data.get("failed", {})
                    self.metadata = data.get("metadata", {})
            except Exception:
                # Start fresh if state file is corrupted
                pass

    def save_state(self):
        """Save state to disk"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "completed": list(self.completed_entities),
            "failed": self.failed_entities,
            "metadata": self.metadata,
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def mark_completed(self, entity_id: str):
        """Mark entity as successfully processed"""
        self.completed_entities.add(entity_id)
        self.failed_entities.pop(entity_id, None)
        self.save_state()

    def mark_failed(self, entity_id: str, error: str):
        """Mark entity as failed with error"""
        self.failed_entities[entity_id] = error
        self.save_state()

    def is_completed(self, entity_id: str) -> bool:
        """Check if entity was already processed"""
        return entity_id in self.completed_entities

    def get_failed_entities(self) -> Dict[str, str]:
        """Get all failed entities with their errors"""
        return self.failed_entities.copy()

    def reset(self):
        """Reset all state"""
        self.completed_entities.clear()
        self.failed_entities.clear()
        self.metadata.clear()
        self.save_state()

    def reset_failed_entities(self):
        """Remove failed entities from completed state so they can be retried"""
        failed_ids = set(self.failed_entities.keys())
        self.completed_entities -= failed_ids
        self.failed_entities.clear()
        self.save_state()


def save_json(data: Any, file_path: Path):
    """Save data as JSON with error handling"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except PermissionError:
        raise IOError(f"Permission denied writing to {file_path}")
    except OSError as e:
        if e.errno == 28:  # No space left on device
            raise IOError(f"No space left on device when writing to {file_path}")
        elif e.errno == 36:  # File name too long
            raise IOError(f"File name too long: {file_path}")
        else:
            raise IOError(f"Filesystem error writing to {file_path}: {e}")
    except Exception as e:
        raise IOError(f"Failed to save JSON to {file_path}: {e}")
