"""
hotel_agent.py

"""

import requests as r
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, initialize_agent, AgentType


class HotelAgent:
    def __init__(self, config):
        self.config = config
        self.geolocator = Nominatim(user_agent="hotel_app_geolocator")
        self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1)
        self._setup_tools()
        self._setup_llm()
        # self._setup_agent()

    def _setup_tools(self):
        self.tools = []

    def _setup_llm(self, model_temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    # def _setup_agent(self):
    #     self.agent = initialize_agent(
    #         tools=self.tools,
    #         llm=self.llm,
    #         agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    #         verbose=True,
    #     )

    def find_hotels(self, params):
        pass

    def fetch_hotels_from_booking(self, params):
        if not self.config.BOOKING_API_KEY:
            raise Exception("Missing Booking API key")

        headers = {
            "X-RapidAPI-Key": self.config.BOOKING_API_KEY,
            "X-RapidAPI-Host": self.config.BOOKING_API_HOST,
        }

        # First get city ID (dest_id)
        dest_url = "https://booking-com.p.rapidapi.com/v1/hotels/locations"
        dest_query = {
            "name": params["city"],
            "locale": "pl",
            "country": params["country"],
        }

        dest_resp = r.get(dest_url, headers=headers, params=dest_query)
        if dest_resp.status_code != 200:
            raise Exception("Failed to fetch location from Booking API.")

        dest_data = dest_resp.json()
        if not dest_data:
            raise Exception("No location found for the given city.")

        dest_id = dest_data[0].get("dest_id")
        if not dest_id:
            raise Exception("Missing location identifier in API response.")

        api_order_by = (
            params["sort_by"]
            if params["sort_by"] in ["price", "popularity", "review_score"]
            else "price"
        )

        search_url = "https://booking-com.p.rapidapi.com/v1/hotels/search"
        search_params = {
            "checkout_date": params["checkout_date"],
            "checkin_date": params["checkin_date"],
            "dest_type": "city",
            "dest_id": dest_id,
            "locale": "pl",
            "adults_number": params["adults_number"],
            "order_by": api_order_by,
            "filter_by_currency": params["currency"],
            "room_number": params["room_number"],
            "price_min": params["min_price"],
            "price_max": params["max_price"],
            "stars": ",".join(str(s) for s in params["stars"]),
            "page_number": "0",
            "units": "metric",
        }

        resp = r.get(search_url, headers=headers, params=search_params)
        if resp.status_code != 200:
            raise Exception("Failed to fetch hotels from Booking API.")

        data = resp.json()
        hotels_raw = data.get("result", [])
        hotels = []

        for h in hotels_raw:
            price = h.get("min_total_price")
            if price is None or not (
                params["min_price"] <= price <= params["max_price"]
            ):
                continue

            review_score = h.get("review_score")
            try:
                review_score = float(review_score)
            except (ValueError, TypeError):
                review_score = None

            if review_score is None or review_score < params["min_review_score"]:
                continue

            lat = h.get("latitude")
            lon = h.get("longitude")
            coords = (lat, lon) if lat is not None and lon is not None else None

            hotels.append(
                {
                    "name": h.get("hotel_name", "Unknown name"),
                    "price": price,
                    "review_score": h.get("review_score", "Unavailable"),
                    "location": h.get("address", "No data"),
                    "link": f"https://www.booking.com/hotel/{h.get('hotel_id')}.html",
                    "coords": coords,
                }
            )

        return hotels

    def call_gemini_fix_names_and_addresses(self, attractions_json, hotels_json):
        """
        Simulates a Gemini (LLM) call to fix and translate names and addresses.
        In a real application, call the Gemini API (or OpenAI), adjust the prompt, and parse the response.
        """
        prompt = f"""
        Attractions JSON:

        {json.dumps(attractions_json, ensure_ascii=False)}

        Try to find the Polish version of the attraction name and address. If neither can be found, remove the object. The output JSON should contain only name and address.

        Hotels JSON:

        {json.dumps(hotels_json, ensure_ascii=False)}

        Format addresses like: "Księcia Józefa Poniatowskiego, 03-901 Warsaw, Poland" — full words, no abbreviations, no extra words like "street" unless they are part of the name, and include street name, postal code, city, and country.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )
        text = response.choices[0].message["content"]
        try:
            fixed_data = json.loads(text)
        except Exception:
            fixed_data = {
                "attractions": attractions_json["attractions"],
                "hotels": hotels_json["hotels"],
            }
        return fixed_data

    def geocode_address(self, address, retries=3, delay=1):
        if not address:
            return None
        for attempt in range(retries):
            try:
                loc = self.geolocator.geocode(address, timeout=3)
                if loc:
                    return (loc.latitude, loc.longitude)
                else:
                    return None
            except GeocoderTimedOut:
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    return None
            except GeocoderUnavailable:
                st.warning(
                    "Nominatim server is temporarily unavailable. Please try again later."
                )
                return None
        return None

    def distance_km(self, coord1, coord2):
        if coord1 is None or coord2 is None:
            return float("inf")
        return geodesic(coord1, coord2).km

    def enrich_hotels_with_distances(self, hotels, attractions):
        for hotel in hotels:
            hotel_coord = hotel.get("coords")
            distances = []
            for attr in attractions:
                attr_coord = attr.get("coords")
                if hotel_coord and attr_coord:
                    dist = self.distance_km(hotel_coord, attr_coord)
                    distances.append(dist)
            hotel["distances_to_attractions"] = distances
            hotel["avg_distance"] = (
                round(sum(distances) / len(distances), 2) if distances else None
            )
        return hotels

    def check_nominatim_exists(self, location, name) -> bool:
        loc1 = self.geocode_address(location)
        if loc1:
            return True
        loc2 = self.geocode_address(name)
        return bool(loc2)

    def filter_valid_locations(self, items):
        filtered = []
        for obj in items:
            if self.check_nominatim_exists(
                obj.get("location", ""), obj.get("name", "")
            ):
                filtered.append(obj)
        return filtered

    def get_valid_locations_with_coords(self, items):
        valid = []
        for obj in items:
            if "coords" in obj and obj["coords"]:
                valid.append(obj)
                continue

            address = obj.get("location", "")
            name = obj.get("name", "")
            loc = None
            if address:
                loc = self.geocode(address)
            if not loc and name:
                loc = self.geocode(name)

            if loc:
                obj["coords"] = (loc.latitude, loc.longitude)
                valid.append(obj)

        return valid
