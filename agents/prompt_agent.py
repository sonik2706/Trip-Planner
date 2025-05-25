"""
prompt_agent.py


"""
import yaml
import json
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate    

from settings.config import config

class PromptAgent:
    def __init__(self):
        self._load_prompts("prompts/prompt_agent_prompt.yaml")
        self._setup_tools()
        self._setup_llm()

    def _load_prompts(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.prompts = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading prompts: {e}")

    def _setup_tools(self):
        self.tools = []

    def _setup_llm(self, model_temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )
    
    def extract(self, couontry: str, city: str, user_description: str) -> dict:
        """
        Extracts structured travel preferences from a user's description using an LLM.

        Args:
            country (str): Destination country.
            city (str): Destination city.
            user_description (str): Free-text input with travel preferences.

        Returns:
            dict: Extracted preferences or error info.
        """
        prompt = PromptTemplate.from_template(self.prompts["template"])
        chain = prompt | self.llm 

        response = chain.invoke({
            "country": couontry,
            "city": city,
            "user_description": user_description
        })

        try:
            # Handle response from Gemini, which is an AIMessage
            if isinstance(response, AIMessage):
                text = response.content
            else:
                text = str(response)

            # Strip triple backticks and optional "json" label
            if text.startswith("```"):
                text = text.strip("`").strip()
                if text.lower().startswith("json"):
                    text = text[4:].strip()  # remove "json" + newline

            # Parse as JSON
            return json.loads(text)

        except Exception as e:
            return {"error": f"Failed to parse JSON: {str(e)}", "raw": str(response)}