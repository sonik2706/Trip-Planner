"""
config.py

Loads configuration settings from environment variables using Pydantic:
- GEMINI API key
- TAVILY API key
- DISTANCE_MATRIX API key
- BOOKING API key
- BOOKING API HOST key
"""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    GEMINI_API_KEY: str
    TAVILY_API_KEY: str
    DISTANCE_MATRIX_API_KEY: str
    BOOKING_API_KEY: str
    BOOKING_API_HOST: str

    class Config:
        env_file = ".env"


config = Config()
