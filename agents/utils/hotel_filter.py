import requests as r
from typing import Dict, Any, List
from settings.config import config


class HotelFilter:
    def __init__(self):
        self.api_key = config.BOOKING_API_KEY
        self.api_host = config.BOOKING_API_HOST

    def _get_raw_locations(self, city: str) -> List[dict]:
        """Fetch full raw location list for city"""
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        params = {"name": city, "locale": "en-gb"}
        url = "https://booking-com.p.rapidapi.com/v1/hotels/locations"

        response = r.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Location API error {response.status_code}")

        data = response.json()
        if not data:
            raise Exception(f"No results found for {city}")
        return data

    def get_filter_options(
        self,
        dest_id: str,
        dest_type: str,
        checkin_date: str,
        checkout_date: str,
        adults_number: int,
        children_number: int,
        children_ages: str,
        locale: str = "en-gb",
        currency: str = "PLN",
        units: str = "metric",
        order_by: str = "popularity",
        room_number: int = 1,
        page_number: int = 0
    ) -> dict[Any, dict[Any, dict[str, Any]]]:
        """
        Fetches available filter options from the Booking.com API.

        Returns:
            A dictionary where:
            - each key is the filter category name (e.g. 'Facilities')
            - each value is a dictionary of {user-visible label: API value}
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }

        url = f"https://{self.api_host}/v1/hotels/search-filters"
        params = {
            "children_ages": children_ages,
            "order_by": order_by,
            "filter_by_currency": currency,
            "dest_id": dest_id,
            "dest_type": dest_type,
            "include_adjacency": "true",
            "room_number": room_number,
            "adults_number": adults_number,
            "checkin_date": checkin_date,
            "children_number": children_number,
            "page_number": page_number,
            "checkout_date": checkout_date,
            "locale": locale,
            "units": units
        }

        try:
            response = r.get(url, headers=headers, params=params)
            print(f"[FILTER API] Status: {response.status_code}")
            if response.status_code != 200:
                raise Exception(f"Filter API failed: {response.status_code}")

            data = response.json()
            filters = data.get("filter", [])

            result = {}
            for group in filters:
                title = group.get("title", "Unknown")
                options = {
                    item.get("name"): {
                        "id": item.get("id"),
                        "count": item.get("count", 0)
                    }
                    for item in group.get("categories", [])
                    if item.get("id") and item.get("name")
                }
                if options:
                    result[title] = options

            return result

        except Exception as e:
            print(f"[FILTER API ❌] Error: {str(e)}")
            raise
