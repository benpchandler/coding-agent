"""
Utility functions for handling JSON files.
"""

import json
import os
from typing import Any, Dict, Optional

def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a JSON file and return its contents.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        Optional[Dict[str, Any]]: The loaded JSON data or None if loading fails
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {str(e)}")
        return None

def save_json(file_path: str, data: Dict[str, Any], indent: int = 4) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        file_path (str): Path where to save the JSON file
        data (Dict[str, Any]): Data to save
        indent (int, optional): Number of spaces for indentation. Defaults to 4.
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {str(e)}")
        return False

def merge_json_objects(obj1, obj2):
    """Merge two JSON objects"""
    result = obj1.copy()
    
    for key, value in obj2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_json_objects(result[key], value)
        else:
            result[key] = value
            
    return result

def json_serialize_datetime(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")