"""
Prompt loader utility for managing LLM prompts.

Supports two template types:
- Simple: Python .format() style with {variable} placeholders
- Jinja2: Full Jinja2 templating for complex prompts with conditionals/includes
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
import yaml

# Directory containing prompt YAML files
PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=16)
def _load_yaml_file(filename: str) -> dict:
    """Load and cache a YAML prompt file."""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f'Prompt file not found: {filepath}')

    with open(filepath, encoding='utf-8') as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def _get_jinja_env() -> Environment:
    """Get cached Jinja2 environment with prompts directory as loader."""
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def get_prompt_template(prompt_file: str, prompt_name: str) -> str:
    """
    Get the raw template string for a prompt.

    Args:
        prompt_file: Name of the YAML file (without .yaml extension)
        prompt_name: Name of the prompt within the file

    Returns:
        Raw template string
    """
    data = _load_yaml_file(f'{prompt_file}.yaml')
    prompts = data.get('prompts', {})

    if prompt_name not in prompts:
        raise KeyError(
            f"Prompt '{prompt_name}' not found in {prompt_file}.yaml. "
            f'Available prompts: {list(prompts.keys())}'
        )

    return prompts[prompt_name].get('template', '')


def load_prompt(prompt_file: str, prompt_name: str, **variables: Any) -> str:
    """
    Load and render a prompt template with variables.

    Args:
        prompt_file: Name of the YAML file (without .yaml extension)
        prompt_name: Name of the prompt within the file
        **variables: Variables to substitute into the template

    Returns:
        Rendered prompt string

    Examples:
        >>> prompt = load_prompt("alert_recommender", "new_user",
        ...     address_city="Austin",
        ...     address_state="TX"
        ... )
    """
    data = _load_yaml_file(f'{prompt_file}.yaml')
    metadata = data.get('metadata', {})
    template_type = metadata.get('template_type', 'simple')

    template_str = get_prompt_template(prompt_file, prompt_name)

    if template_type == 'jinja2':
        # Use Jinja2 for complex templates
        env = _get_jinja_env()
        template = env.from_string(template_str)
        return template.render(**variables)
    else:
        # Use simple Python format for basic templates
        return template_str.format(**variables)


def load_schema() -> str:
    """Load the shared database schema definition."""
    schema_path = PROMPTS_DIR / 'schema.yaml'
    if not schema_path.exists():
        raise FileNotFoundError(f'Schema file not found: {schema_path}')

    with open(schema_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('schema', '')


def clear_cache() -> None:
    """Clear all cached prompt data. Useful for testing or hot-reloading."""
    _load_yaml_file.cache_clear()
    _get_jinja_env.cache_clear()
