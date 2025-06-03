import os
import json

from langchain.agents import Tool, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import initialize_agent
from dotenv import load_dotenv
from typing import Optional
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from agents.utils.json_formatter import GenericLLMFormatter
from agents.utils.prompt import load_prompts

class AttractionAgent:

    def __init__(self, config):
        self.config = config
        self.prompts = load_prompts("prompts/attraction_agent_prompt.yaml")
        self._setup_llm()
        self._setup_tools()
        self._setup_agent()

    def _setup_llm(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    def _setup_tools(self):
        tavily_tool = TavilySearchResults(tavily_api_key=self.config.TAVILY_API_KEY)
        self.tools = [
            Tool(
                name="Tavily Web Search",
                func=tavily_tool.invoke,
                description="Search the web for travel information, tourist attractions, or recent travel blog content.",
            )
        ]

    def _setup_agent(self):
        self.data_gathering_agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
        )

    def find_attractions(
        self, city_name: str, num_attractions: int, focus: Optional[str] = None
    ) -> dict:
        """
        Retrieve top tourist attractions in a city, optionally filtered by focus.

        Args:
            city_name (str): City to search attractions in.
            num_attractions (int): Number of attractions to return.
            focus (Optional[str], optional): Theme to filter attractions. Defaults to None.

        Returns:
            str: JSON string with attraction details.
        """
        # Format the focus clause for the prompt
        focus_clause = f" related to {focus}" if focus else ""

        # Use the prompt template from the YAML file
        data_gathering_prompt = self.prompts["data_gathering_prompt_template"].format(
            num_attractions=num_attractions,
            city_name=city_name,
            focus_clause=focus_clause,
        )

        # Get raw data from the agent
        raw_data = self.data_gathering_agent.invoke(data_gathering_prompt)

        # Now use a separate LLM call to format the results as JSON
        formatter = GenericLLMFormatter(
            llm=self.llm,
            prompt_template_str=self.prompts["json_formatter_template"],
            input_variables=[
                "city_name",
                "raw_data",
                "focus_or_general",
                "num_attractions",
            ],
        )

        json_data = formatter.run(
            city_name=city_name,
            raw_data=raw_data,
            focus_or_general=focus if focus else "general",
            num_attractions=num_attractions,
        )

        return json_data

