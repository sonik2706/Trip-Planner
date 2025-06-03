import json

import requests as r
from urllib.parse import quote_plus
from typing import List, Dict

from settings.config import config


class LocationGeocoder:
    def __init__(self):
        self.api_key = config.DISTANCE_MATRIX_API_KEY

    def get_coordinates(self, location: str) -> List[float] | None:
        """
        Get the geographic coordinates (latitude and longitude) of a location using Google Maps Geocoding API.
        Returns None if not found.
        """
        try:
            encoded_location = quote_plus(location)
            url = (
                f"https://maps.googleapis.com/maps/api/geocode/json"
                f"?address={encoded_location}&key={self.api_key}"
            )
            response = r.get(url)
            data = response.json()

            if data["status"] != "OK" or not data["results"]:
                return None

            location_data = data["results"][0]["geometry"]["location"]
            return [location_data["lat"], location_data["lng"]]
        except Exception:
            return None

    def get_attraction_coordinates(self, data: dict) -> List[Dict[str, List[float]]]:
        """
        Given a data dictionary containing a list of attractions,
        returns a list of dicts with name and coordinates.
        """
        assert isinstance(data, dict), "Expected input data to be a dict"

        results = []
        city = data.get("city", "")

        for attraction in data.get("attractions", []):
            name = attraction.get("name")
            if not name:
                continue
            full_name = f"{name}, {city}"
            coords = self.get_coordinates(full_name)
            if coords:
                results.append({"name": name, "coords": coords})

        return results
