import json
import requests
from typing import Dict, List, Optional, Literal
from datetime import date, datetime
from urllib.parse import quote_plus

import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from settings.config import config

class BookingAgent:
    def __init__(self, model_temperature: float = 0.0):
        self._load_prompts("prompts/booking_agent_prompt.yaml")
        self._setup_llm(model_temperature)
        self._setup_tools()
        self._setup_agent()

    def _load_prompts(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.prompts = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            # Fallback prompts
            self.prompts = {
                'search_template': '''
                Search for hotels in {city}, {country} for {checkin_date} to {checkout_date}.
                Requirements:
                - Adults: {adults_number}
                - Rooms: {room_number}
                - Price range: {min_price} - {max_price} {currency}
                - Minimum review score: {min_review_score}
                - Stars: {stars}

                Use available tools to find the best hotels matching these criteria.
                ''',
                'filter_template': '''
                Filter and rank the following hotels based on criteria:
                Hotels data: {hotels_data}
                Sort by: {sort_by}
                Max results: {max_hotels}

                Return only the best matches in JSON format.
                '''
            }

    def _setup_llm(self, model_temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=config.GEMINI_API_KEY,
            temperature=model_temperature,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    def _setup_tools(self):
        self.tools = [
            Tool(
                name="search_hotels_booking_api",
                func=self._search_hotels_api,
                description=(
                    "Search for hotels using Booking.com API. "
                    "Input should be a JSON string with search parameters."
                )
            ),
            Tool(
                name="get_location_id",
                func=self._get_location_id,
                description=(
                    "Get destination ID for a city using Booking.com API. "
                    "Input should be city name and optionally country."
                )
            ),
            Tool(
                name="filter_hotels_by_criteria",
                func=self._filter_hotels,
                description=(
                    "Filter hotels by price, rating, and other criteria. "
                    "Input should be JSON with hotels data and filter criteria."
                )
            )
        ]

    def _setup_agent(self):
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

    def _get_location_id(self, location_query: str) -> str:
        """Get destination ID for a location"""
        try:
            # Parse query if it's JSON, otherwise treat as simple string
            if location_query.strip().startswith('{'):
                query_data = json.loads(location_query)
                city = query_data.get('city', '')
                country = query_data.get('country', '')
            else:
                city = location_query.strip()
                country = ''

            headers = {
                "X-RapidAPI-Key": config.BOOKING_API_KEY,
                "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
            }

            dest_url = "https://booking-com.p.rapidapi.com/v1/hotels/locations"
            dest_query = {
                "name": city,
                "locale": "en-gb"
            }

            if country:
                dest_query["country"] = country

            response = requests.get(dest_url, headers=headers, params=dest_query)

            if response.status_code != 200:
                return f"Error: Failed to get location ID. Status: {response.status_code}"

            data = response.json()
            if not data:
                return f"No location found for: {city}"

            dest_id = data[0].get("dest_id")
            if not dest_id:
                return f"No destination ID found for: {city}"

            return json.dumps({
                "dest_id": dest_id,
                "city": city,
                "country": country,
                "status": "success"
            })

        except Exception as e:
            return f"Error getting location ID: {str(e)}"

    def _search_hotels_api(self, search_params: str) -> str:
        """Search for hotels using Booking.com API"""
        try:
            params = json.loads(search_params)

            # Get destination ID first
            location_result = self._get_location_id(json.dumps({
                "city": params.get("city", ""),
                "country": params.get("country", "")
            }))

            location_data = json.loads(location_result)
            if location_data.get("status") != "success":
                return location_result

            dest_id = location_data["dest_id"]

            headers = {
                "X-RapidAPI-Key": config.BOOKING_API_KEY,
                "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
            }

            search_url = "https://booking-com.p.rapidapi.com/v1/hotels/search"
            search_query = {
                "dest_id": dest_id,
                "dest_type": "city",
                "checkin_date": params.get("checkin_date"),
                "checkout_date": params.get("checkout_date"),
                "adults_number": params.get("adults_number", 2),
                "room_number": params.get("room_number", 1),
                "locale": "en-gb",
                "currency": params.get("currency", "USD"),
                "order_by": params.get("sort_by", "price"),
                "filter_by_currency": params.get("currency", "USD"),
                "page_number": "0",
                "units": "metric"
            }

            if params.get("min_price"):
                search_query["price_min"] = params["min_price"]
            if params.get("max_price"):
                search_query["price_max"] = params["max_price"]

            response = requests.get(search_url, headers=headers, params=search_query)

            print(f"🔍 Response status: {response.status_code}")
            print(f"🔍 Response body: {response.text[:300]}")  # ogranicz do 300 znaków

            if response.status_code != 200:
                return f"Error: Failed to search hotels. Status: {response.status_code}"

            try:
                data = response.json()
            except json.JSONDecodeError:
                return f"Error: Failed to decode JSON. Raw response: {response.text[:300]}"

            hotels_raw = data.get("result", [])

            hotels = []
            for hotel in hotels_raw:
                price = hotel.get("min_total_price")
                if price is None:
                    continue

                review_score = hotel.get("review_score")
                try:
                    review_score = float(review_score) if review_score else 0
                except (ValueError, TypeError):
                    review_score = 0

                lat = hotel.get("latitude")
                lon = hotel.get("longitude")
                coords = (lat, lon) if lat is not None and lon is not None else None

                hotels.append({
                    "name": hotel.get("hotel_name", "Unknown"),
                    "price": price,
                    "review_score": review_score,
                    "location": hotel.get("address", "No address"),
                    "link": f"https://www.booking.com/hotel/{hotel.get('hotel_id')}.html",
                    "coords": coords,
                    "hotel_id": hotel.get("hotel_id"),
                    "stars": hotel.get("class"),
                    "description": hotel.get("hotel_name_trans", "")
                })

            return json.dumps({
                "hotels": hotels,
                "total_found": len(hotels),
                "status": "success"
            }, ensure_ascii=False)

        except Exception as e:
            return f"Error searching hotels: {str(e)}"

    def _filter_hotels(self, filter_params: str) -> str:
        """Filter and sort hotels based on criteria"""
        try:
            params = json.loads(filter_params)
            hotels = params.get("hotels", [])

            # Apply filters
            filtered_hotels = []
            for hotel in hotels:
                # Price filter
                price = hotel.get("price", 0)
                if params.get("min_price") and price < params["min_price"]:
                    continue
                if params.get("max_price") and price > params["max_price"]:
                    continue

                # Review score filter
                review_score = hotel.get("review_score", 0)
                if params.get("min_review_score") and review_score < params["min_review_score"]:
                    continue

                # Stars filter
                stars = hotel.get("stars")
                if params.get("stars") and stars not in params["stars"]:
                    continue

                filtered_hotels.append(hotel)

            # Sort hotels
            sort_by = params.get("sort_by", "price")
            if sort_by == "price":
                filtered_hotels.sort(key=lambda x: x.get("price", float('inf')))
            elif sort_by == "review_score":
                filtered_hotels.sort(key=lambda x: x.get("review_score", 0), reverse=True)
            elif sort_by == "shortest_distance":
                filtered_hotels.sort(key=lambda x: x.get("avg_distance", float('inf')))

            # Limit results
            max_hotels = params.get("max_hotels", 10)
            filtered_hotels = filtered_hotels[:max_hotels]

            return json.dumps({
                "hotels": filtered_hotels,
                "total_filtered": len(filtered_hotels),
                "status": "success"
            }, ensure_ascii=False)

        except Exception as e:
            return f"Error filtering hotels: {str(e)}"

    def search_hotels(
            self,
            city: str,
            country: str = "",
            checkin_date: str = "",
            checkout_date: str = "",
            adults_number: int = 2,
            room_number: int = 1,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            currency: str = "USD",
            stars: Optional[List[int]] = None,
            min_review_score: float = 0.0,
            sort_by: Literal["price", "review_score", "shortest_distance"] = "price",
            max_hotels: int = 10
    ) -> Dict:
        """
        Search for hotels using the agent and tools.

        Args:
            city: Target city name
            country: Country name (optional)
            checkin_date: Check-in date in YYYY-MM-DD format
            checkout_date: Check-out date in YYYY-MM-DD format
            adults_number: Number of adults
            room_number: Number of rooms
            min_price: Minimum price filter
            max_price: Maximum price filter
            currency: Currency code (USD, EUR, PLN, etc.)
            stars: List of acceptable star ratings
            min_review_score: Minimum review score
            sort_by: Sorting criteria
            max_hotels: Maximum number of results

        Returns:
            Dict: Search results with hotels data
        """

        # Prepare search parameters
        search_params = {
            "city": city,
            "country": country,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "adults_number": adults_number,
            "room_number": room_number,
            "currency": currency,
            "sort_by": sort_by,
            "min_price": min_price,
            "max_price": max_price,
            "stars": stars,
            "min_review_score": min_review_score,
            "max_hotels": max_hotels
        }

        # Create prompt for the agent
        prompt = self.prompts.get('search_template', '').format(**search_params)

        try:
            # Use the agent to search for hotels
            response = self.agent.invoke(prompt)

            # Parse response if it's a string containing JSON
            if isinstance(response, str):
                try:
                    response_data = json.loads(response)
                except json.JSONDecodeError:
                    response_data = {"hotels": [], "status": "error", "message": response}
            else:
                response_data = response

            return response_data

        except Exception as e:
            return {
                "hotels": [],
                "status": "error",
                "message": f"Error in hotel search: {str(e)}"
            }

    def enrich_hotels_with_distances(self, hotels: List[Dict], attractions: List[Dict]) -> List[Dict]:
        """
        Calculate distances from hotels to attractions and enrich hotel data.

        Args:
            hotels: List of hotel dictionaries
            attractions: List of attraction dictionaries with coordinates

        Returns:
            List[Dict]: Enriched hotels with distance information
        """
        from geopy.distance import geodesic

        enriched_hotels = []

        for hotel in hotels:
            hotel_coord = hotel.get("coords")
            if not hotel_coord:
                continue

            distances = []
            for attraction in attractions:
                attr_coord = attraction.get("coords")
                if attr_coord:
                    try:
                        dist = geodesic(hotel_coord, attr_coord).kilometers
                        distances.append(round(dist, 2))
                    except Exception:
                        continue

            if distances:
                hotel["distances_to_attractions"] = distances
                hotel["avg_distance"] = round(sum(distances) / len(distances), 2)
                enriched_hotels.append(hotel)

        return enriched_hotels