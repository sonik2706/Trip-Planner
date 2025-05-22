"""
config.py

Loads configuration settings from environment variables using Pydantic:
- OpenAI API key

"""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    GEMINI_API_KEY: str
    TAVILY_API_KEY: str
    LLM_MODEL: str
    DISTANCE_MATRIX_API_KEY: str

    class Config:
        env_file = ".env"


config = Config()
