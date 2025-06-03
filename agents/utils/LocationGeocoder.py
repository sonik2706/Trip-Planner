import json
import time

import requests as r
from urllib.parse import quote_plus
from typing import List, Dict

from agents.utils import location_normalizer
from agents.utils.location_normalizer import LocationNormalizer
from settings.config import config


class LocationGeocoder:
    def __init__(self):
        self.api_key = config.DISTANCE_MATRIX_API_KEY
        self.normalizer = LocationNormalizer(config)

    def get_coordinates(self, location: str) -> List[float] | None:
        """
        Try OpenStreetMap first. If it fails, fall back to Google Maps Geocoding API.
        """

        # 🔍 First try OpenStreetMap
        coords = self._get_from_osm(location)
        if coords:
            print(f"[OSM ✅] {location} → {coords}")
            return coords

        # ❗Fallback to Google
        for attempt in range(2):
            try:
                print(f"[GOOGLE ATTEMPT {attempt + 1}] {location}")
                coords = self._get_from_google(location)
                if coords:
                    print(f"[GOOGLE ✅] {location} → {coords}")
                    return coords
            except Exception as e:
                print(f"[GOOGLE ❌] Error: {e}")
                time.sleep(1)

        print(f"[FAIL] No coordinates found for: {location}")
        return None

    def _get_from_osm(self, location: str) -> List[float] | None:
        try:
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                "q": location,
                "format": "json",
                "limit": 1
            }
            headers = {
                "User-Agent": "AITripPlanner/1.0"
            }
            response = r.get(url, params=params, headers=headers)
            data = response.json()

            if not data:
                print(f"[OSM ❌] No results for: {location}")
                return None

            return [float(data[0]["lat"]), float(data[0]["lon"])]
        except Exception as e:
            print(f"[OSM ❌] Error: {e}")
            return None

    def _get_from_google(self, location: str) -> List[float] | None:
        encoded_location = quote_plus(location)
        url = (
            f"https://maps.googleapis.com/maps/api/geocode/json"
            f"?address={encoded_location}&key={self.api_key}"
        )
        response = r.get(url)
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            print(f"[GOOGLE ❌] No results for: {location}")
            return None

        loc = data["results"][0]["geometry"]["location"]
        return [loc["lat"], loc["lng"]]

    def get_attraction_coordinates(self, data: dict) -> List[Dict[str, List[float]]]:
        """
        Given a data dictionary containing a list of attractions,
        returns a list of dicts with name and coordinates.
        """
        assert isinstance(data, dict), "Expected input data to be a dict"

        results = []
        city = data.get("city", "")
        attractions = data.get("attractions", [])

        # 1. Zbierz nazwy
        names = [a.get("name") for a in attractions if a.get("name")]

        # 2. Użyj bulk normalizacji
        normalized_map = self.normalizer.normalize_all(names)

        # 3. Iteruj po atrakcjach
        for attraction in attractions:
            original_name = attraction.get("name")
            if not original_name:
                continue
            normalized = normalized_map.get(original_name, original_name)
            full_name = f"{normalized}, {city}"
            coords = self.get_coordinates(full_name)
            if coords:
                results.append({"name": original_name, "coords": coords})

        return results
