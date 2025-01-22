import hashlib
import os
import yaml
from typing import Dict, List, Type
from pydantic import BaseModel, ValidationError

from depictio_models.logging import logger
from depictio_models.models.base import PyObjectId, convert_objectid_to_str


def get_depictio_context():
    return os.getenv("DEPICTIO_CONTEXT")

def convert_model_to_dict(model: BaseModel) -> Dict:
    """
    Convert a Pydantic model to a dictionary.
    """
    return convert_objectid_to_str(model.model_dump())

def get_config(filename: str):
    """
    Get the config file.
    """
    logger.debug("Loading utils.py")

    if not filename.endswith(".yaml"):
        raise ValueError("Invalid config file. Must be a YAML file.")
    if not os.path.exists(filename):
        raise ValueError(f"The file '{filename}' does not exist.")
    if not os.path.isfile(filename):
        raise ValueError(f"'{filename}' is not a file.")
    else:
        with open(filename, "r") as f:
            yaml_data = yaml.safe_load(f)
        return yaml_data


def substitute_env_vars(config: Dict) -> Dict:
    """
    Recursively substitute environment variables in the configuration dictionary.

    Args:
        config (Dict): Configuration dictionary with potential environment variable placeholders.

    Returns:
        Dict: Configuration dictionary with substituted environment variables.
    """
    # Recursively handle environment variables substitution in nested dictionaries and lists
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Substitute environment variables in string values
        return os.path.expandvars(config)
    else:
        return config


def validate_model_config(config: Dict, pydantic_model: Type[BaseModel]) -> BaseModel:
    """
    Load and validate the YAML configuration
    """
    if not isinstance(config, dict):
        raise ValueError("Invalid config. Must be a dictionary.")
    try:
        # List environment variables
        logger.info(f"Env args: {os.environ}")

        # Substitute environment variables within the config
        substituted_config = substitute_env_vars(config)
        logger.info(f"Substituted Config: {substituted_config}")

        # Load the config into a Pydantic model
        data = pydantic_model(**substituted_config)
        logger.info(f"Resulting object model: {data}")
    except ValidationError as e:
        raise ValueError(f"Invalid config: {e}")
    return data
