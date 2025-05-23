"""
map_agent.py

"""

import yaml
import json
import requests as r
from typing import Dict, List, Literal
from urllib.parse import quote_plus

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.prompts import PromptTemplate, load_prompt

from settings.config import config


class MapAgent:
    def __init__(self, model_temperature: float = 0.0):
        self._load_prompts("prompts/map_agent_prompt.yaml")
        self._setup_llm(model_temperature)
        self._setup_tools()
        self._setup_agent()

    def _load_prompts(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.prompts = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading prompts: {e}")
        
    def _setup_tools(self):
        self.tools = [
            Tool(
                name="get_eta",
                func=self._get_eta_from_string,
                description=(
                    "Estimate travel time and distance between two locations. "
                    "Input should be a string like: 'from X to Y using walking|driving|transit'"
                )
            ),
            Tool(
                name="get_coordinates",
                func=self.get_coordinates,
                description="Get latitude and longitude of a location. Input should be a location name or address like 'Colosseum, Rome'."
            )
        ]

    def _setup_llm(self, model_temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    def _setup_agent(self):
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

    def _get_eta_from_string(self, query: str) -> str:
        """
        Parse a natural language input and extract origin, destination, and mode
        Example format: 'from PJATK to Old Town Market Square using walking'
        """
        import re
        pattern = r"from (.+?) to (.+?) using (walking|driving|transit)"
        match = re.search(pattern, query.strip(), re.IGNORECASE)

        if not match:
            return (
                "Invalid input. Use format like: 'from Colosseum to Pantheon using walking'."
            )

        origin = match.group(1).strip()
        destination = match.group(2).strip()
        mode = match.group(3).strip().lower()
        
        return self.get_eta(origin, destination, mode)

    def get_eta(self, origin: str, destination: str, mode: Literal["walking", "driving", "transit"]) -> str:
        """
        Estimate travel time and distance between two locations using the Google Maps Distance Matrix API.

        Args:
            origin (str): The starting location (e.g., "Colosseum, Rome").
            destination (str): The destination location (e.g., "Pantheon, Rome").
            mode (str): Mode of transportation. Must be one of: "walking", "driving", or "transit".

        Returns:
            str: A formatted string showing the estimated travel time and distance.
        """
        try:

            print(origin, destination)
            query = (
                f"https://maps.googleapis.com/maps/api/distancematrix/json"
                f"?origins={quote_plus(origin)}&destinations={quote_plus(destination)}&mode={mode}"
                f"&key={config.DISTANCE_MATRIX_API_KEY}"
            )
            print(query)
            response = r.get(query)
            
            data = response.json()
            print(data)
            element = data["rows"][0]["elements"][0]
            if element.get("status") != "OK":
                return f"Could not get ETA between {origin} and {destination}."

            duration = element["duration"]["text"]
            distance = element["distance"]["text"]

            return f"Estimated time: {duration}, Distance: {distance}, between {origin} and {destination}."
        except Exception as e:
            return f"Error finding ETA between {origin} and {destination}: {str(e)}"

    def get_coordinates(self, location: str) -> str:
        """
        Get the geographic coordinates (latitude and longitude) of a location using Google Maps Geocoding API.

        Args:
            location (str): The name or address of the location (e.g., "Colosseum, Rome").

        Returns:
            str: A formatted string with latitude and longitude, or an error message.
        """
        try:
            encoded_location = quote_plus(location)
            url = (
                f"https://maps.googleapis.com/maps/api/geocode/json"
                f"?address={encoded_location}&key={config.DISTANCE_MATRIX_API_KEY}"
            )
            response = r.get(url)
            data = response.json()

            if data["status"] != "OK":
                return f"Could not get coordinates for {location}."

            result = data["results"][0]["geometry"]["location"]
            lat = result["lat"]
            lng = result["lng"]

            return f"{location} -> Latitude: {lat}, Longitude: {lng}"
        except Exception as e:
            return f"Error finding coordinates for {location}: {str(e)}"

    def generate_google_maps_link(self, attractions: list) -> str:
        """
        Generate a google maps link using the provided attractions list

        Args:
            attractions(list): An ordered list of attractions to be visited

        Returns:
            str: Link to google maps with all the destinations.
        """
        base_url = "https://www.google.com/maps/dir/"

        # Ensure each attraction is converted to a string before applying quote_plus
        return base_url + "/".join(
            quote_plus(str(attraction)) for attraction in attractions
        )

    def optimize(self, city: str, days: int, accomodation_address: str,list_attractions: list) -> Dict:
        """
        Generate an optimized itinerary by estimating ETAs from the accommodation to each attraction.

        Args:
            city (str): Destination city name
            days (int): Number of available sightseeing days
            accomodation_address (str): Starting location
            list_attractions (list): List of attraction names

        Returns:
            Dict: Optimized itinerary or planning result
        """
        prompt = self.prompts['template'].format(
            city=city,
            focus="walking",
            days=days,
            accomodation_address=accomodation_address,
            list_attractions="\n".join(f"- {place}" for place in list_attractions)
        )

        response = self.agent.invoke(prompt)
        
        try:
            data = json.dumps(response)
            print(data["Final Answer"])
        except:
            pass
   