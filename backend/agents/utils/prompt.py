"""
prompt.py
"""

import yaml

def load_prompts(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            prompts = yaml.safe_load(file)
            return prompts
    except Exception as e:
        print(f"Error loading prompts: {e}")