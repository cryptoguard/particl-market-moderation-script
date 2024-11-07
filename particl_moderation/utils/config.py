import yaml
import os

from typing import Any, Dict

CONFIG_FILE = "config.yaml"

class Config:
    def __init__(self):
        self.project_root = self.find_project_root()
        self.config_dir = os.path.join(self.project_root, "config")
        self.ensure_config_dir_exists()
        self.config_path = os.path.join(self.config_dir, CONFIG_FILE)
        self.config = self.load_config()

    def find_project_root(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while True:
            if os.path.exists(os.path.join(current_dir, "pyproject.toml")):
                return current_dir
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                raise FileNotFoundError("Could not find project root")
            current_dir = parent_dir

    def ensure_config_dir_exists(self):
        os.makedirs(self.config_dir, exist_ok=True)

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "particl": {
                "cli_path": "",
                "data_dir": "",
                "active_wallet": "testtest"
            },
            "moderation": {
                "enabled": True,
            },
            "llm": {
                "model": "gemma2:2b",
                "ollama_path": ""
            },
            "logging": {
                "level": "INFO",
                "file": "particl_moderation.log"
            },
            "paths": {
                "cache_file": os.path.join(self.config_dir, "listing_cache.txt"),
                "queue_file": os.path.join(self.config_dir, "queue.txt"),
                "vote_queue_file": os.path.join(self.config_dir, "vote_queue.txt"),
                "results_file": os.path.join(self.config_dir, "results.txt"),
            },
            "rules": {
                "config_file": "rules_config.json",
                "predefined_file": "predefined_rules.json"
            }
        }

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'rb') as f:
                    user_config = yaml.safe_load(f)
                default_config = self.get_default_config()
                self.merge_configs(default_config, user_config)
                return default_config
            except Exception as e:
                print(f"Error loading config file: {str(e)}")
                return self.get_default_config()
        return self.get_default_config()

    def merge_configs(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> None:
        for key, value in user_config.items():
            if isinstance(value, dict) and key in default_config:
                self.merge_configs(default_config[key], value)
            else:
                default_config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save_config()

    def save_config(self) -> None:
        try:
            with open(self.config_path, 'wb') as f:
                yaml_str = yaml.dump(self.config, default_flow_style=False)
                f.write(yaml_str.encode('utf-8'))
        except Exception as e:
            print(f"Error saving config file: {str(e)}")

    def get_full_path(self, key: str) -> str:
        value = self.get(key)
        if value:
            return os.path.join(self.config_dir, value)
        return ""

config = Config()

def get_config(key: str, default: Any = None) -> Any:
    return config.get(key, default)

def set_config(key: str, value: Any) -> None:
    config.set(key, value)

def get_full_path(key: str) -> str:
    return config.get_full_path(key)
