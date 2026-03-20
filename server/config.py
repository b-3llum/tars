"""TARS configuration loader."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based settings."""

    tars_api_key: str = "change-me"
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    tars_host: str = "0.0.0.0"
    tars_port: int = 8400
    rate_limit_rpm: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(name: str) -> dict:
    """Load a YAML file from the config/ directory."""
    config_dir = Path(__file__).resolve().parent.parent / "config"
    path = config_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


@lru_cache
def get_tars_config() -> dict:
    return load_yaml_config("tars.yaml")


@lru_cache
def get_hosts_config() -> dict:
    data = load_yaml_config("hosts.yaml")
    hosts = data.get("hosts", {})
    # Expand ~ in key paths
    for host in hosts.values():
        if "key_path" in host:
            host["key_path"] = os.path.expanduser(host["key_path"])
    return hosts
