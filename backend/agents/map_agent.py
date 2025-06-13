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
from backend.agents.utils.prompt import load_prompts
from backend.agents.utils.json_formatter import GenericLLMFormatter
from backend.agents.utils.LocationGeocoder import LocationGeocoder

class MapAgent:
    def __init__(self, config, model_temperature: float = 0.0):
        self.config = config
        self.prompts = load_prompts("backend/prompts/map_agent_prompt.yaml")
        self._setup_llm(model_temperature)
        self.location_geocoder = LocationGeocoder()
        self._setup_tools()
        self._setup_agent()

    def _get_coordinates_from_string(self, locations_str: str) -> str:
        """
        Parses input like: "city=Rome; attractions=Colosseum, Pantheon, Trevi Fountain"
        Then gets coordinates using location_geocoder
        """
        try:
            # Rozdziel na części
            parts = [part.strip() for part in locations_str.split(";")]
            city = "Unknown"
            attractions = []

            for part in parts:
                if part.startswith("city="):
                    city = part[len("city="):].strip()
                elif part.startswith("attractions="):
                    attractions = [a.strip() for a in part[len("attractions="):].split(",")]

            # Tworzenie struktury danych
            data = {
                "city": city,
                "attractions": [{"name": name} for name in attractions]
            }

            # Wywołanie metody i formatowanie wyników
            results = self.location_geocoder.get_attraction_coordinates(data)
            formatted_results = []
            for result in results:
                name = result.get("name", "Unknown")
                coords = result.get("coords", [])
                if len(coords) >= 2:
                    formatted_results.append(f"{name}: {coords[0]}, {coords[1]}")
                else:
                    formatted_results.append(f"{name}: No coordinates found")
            return "\n".join(formatted_results)

        except Exception as e:
            return f"Error getting coordinates: {str(e)}"


    def _setup_tools(self):
        self.tools = [
            Tool(
                name="get_eta",
                func=self._get_eta_from_string,
                description=(
                    "Estimate travel time and distance between two locations. "
                    "Input should be a string like: 'from X to Y using walking|driving|transit'"
                ),
            ),
            Tool(
                name="get_coordinates",
                func=self._get_coordinates_from_string,  # Use wrapper instead
                description=(
                    "Get the coordinates (latitude and longitude) for multiple attractions in a specific city. "
                    "Input should be in the format: 'city=CityName; attractions=Attraction1, Attraction2, Attraction3'. "
                    "Example: 'city=Rome; attractions=Colosseum, Pantheon, Trevi Fountain'. "
                    "Returns a list of results like: 'Colosseum: 41.89, 12.49'."
                ),
            ),
            Tool(
                name="generate_google_maps_link",
                func=self.generate_google_maps_link,
                description="Generate a Google Maps route link from a comma-separated list of location names (e.g., 'Colosseum, Pantheon, Roman Forum').",
            ),
        ]

    def _setup_llm(self, model_temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.config.GEMINI_API_KEY,
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
            handle_parsing_errors=True
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
            return "Invalid input. Use format like: 'from Colosseum to Pantheon using walking'."

        origin = match.group(1).strip()
        destination = match.group(2).strip()
        mode = match.group(3).strip().lower()

        return self.get_eta(origin, destination, mode)

    def get_eta(
        self,
        origin: str,
        destination: str,
        mode: Literal["walking", "driving", "transit"],
    ) -> str:
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
                f"&key={self.config.DISTANCE_MATRIX_API_KEY}"
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


    def generate_google_maps_link(self, attractions_str: str) -> str:
        """
        Generate a Google Maps route link from a string of attraction names.

        Args:
            attractions_str (str): A comma- or newline-separated list of location names.

        Returns:
            str: Google Maps link with route through these locations.
        """
        attractions = [
            item.strip() for item in attractions_str.split(",") if item.strip()
        ]

        if not attractions:
            return "No valid attractions provided."

        base_url = "https://www.google.com/maps/dir/"

        # Ensure each attraction is converted to a string before applying quote_plus
        return (
            base_url
            + "/".join(quote_plus(str(attraction)) for attraction in attractions) + "/"
        )

    def optimize(
        self,
        city: str,
        days: int,
        accomodation_address: str,
        attractions: list,
        focus: Literal["walking", "driving", "transit"] = "transit",
    ) -> Dict:
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
        prompt = self.prompts["template"].format(
            city=city,
            focus=focus,
            days=days,
            accomodation_address=f"city center, {city}" if accomodation_address == "city center" else accomodation_address,
            list_attractions=attractions,
        )

        raw_data = self.agent.invoke(prompt)

        formatter = GenericLLMFormatter(
            llm=self.llm,
            prompt_template_str=self.prompts["json_formatter_template"],
            input_variables=["raw_data"]
        )

        json_data = formatter.run(
            raw_data=raw_data,
        )
        
        print(json_data)
        return json_data
