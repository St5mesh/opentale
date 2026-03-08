"""Configuration for the book generation system"""
import os
from typing import Dict, List

def get_config(local_url: str = None) -> Dict:
    """Get the configuration for the agents
    
    Args:
        local_url: The base URL of your local LLM server's OpenAI-compatible API endpoint.
                   Defaults to environment variable LLM_URL or http://localhost:1234/v1
    """
    
    # Use provided URL, environment variable, or default
    if local_url is None:
        local_url = os.getenv('LLM_URL', 'http://localhost:1234/v1')
    
    # Get model name from environment or use default
    model_name = os.getenv('LLM_MODEL', 'gemma:latest')
    
    # Basic config for local LLM
    config_list = [{
        'model': model_name,
        'base_url': local_url,
        'api_key': "not-needed"
    }]

    # Common configuration for all agents
    agent_config = {
        "seed": 42,
        "temperature": float(os.getenv('LLM_TEMPERATURE', '0.7')),
        "config_list": config_list,
        "timeout": int(os.getenv('LLM_TIMEOUT', '600')),
        "cache_seed": None
    }
    
    return agent_config


def get_narrative_config() -> Dict:
    """Get configuration for narrative engine features.
    
    Returns:
        Dict with settings for scene chains, state tracking, etc.
    """
    return {
        'scene_chain_enabled': True,
        'state_tracking_enabled': True,
        'character_arcs_enabled': True,
        'theme_extraction_enabled': True,
        'scenes_per_chapter': int(os.getenv('SCENES_PER_CHAPTER', '5')),
        'state_history_limit': int(os.getenv('STATE_HISTORY_LIMIT', '100')),
    }