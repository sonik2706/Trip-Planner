#!/usr/bin/env python3
"""
Test script for BookingAgent
Run this to test the BookingAgent independently
"""

import json
import sys
import os
from datetime import date, timedelta

# Add the parent directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.booking_agent import BookingAgent


def test_basic_hotel_search():
    """Test basic hotel search functionality"""
    print("🧪 Testing Basic Hotel Search...")

    agent = BookingAgent(model_temperature=0.1)

    # Test parameters
    test_params = {
        "city": "Warsaw",
        "country": "Poland",
        "checkin_date": (date.today() + timedelta(days=7)).isoformat(),
        "checkout_date": (date.today() + timedelta(days=10)).isoformat(),
        "adults_number": 2,
        "room_number": 1,
        "min_price": 50.0,
        "max_price": 300.0,
        "currency": "PLN",
        "stars": [3, 4, 5],
        "min_review_score": 7.0,
        "sort_by": "price",
        "max_hotels": 5
    }

    try:
        result = agent.search_hotels(**test_params)

        print(f"✅ Status: {result.get('status', 'unknown')}")

        if result.get('status') == 'success' and 'hotels' in result:
            hotels = result['hotels']
            print(f"✅ Found {len(hotels)} hotels")

            # Display first hotel details
            if hotels:
                hotel = hotels[0]
                print(f"\n📍 Sample Hotel:")
                print(f"   Name: {hotel.get('name', 'N/A')}")
                print(f"   Price: {hotel.get('price', 'N/A')} {test_params['currency']}")
                print(f"   Rating: {hotel.get('review_score', 'N/A')}/10")
                print(f"   Location: {hotel.get('location', 'N/A')}")
                print(f"   Coordinates: {hotel.get('coords', 'N/A')}")
        else:
            print(f"❌ Search failed: {result.get('message', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()


def test_location_id_retrieval():
    """Test location ID retrieval"""
    print("\n🧪 Testing Location ID Retrieval...")

    agent = BookingAgent()

    test_cities = [
        {"city": "Paris", "country": "France"},
        {"city": "London", "country": "UK"},
        {"city": "Tokyo", "country": "Japan"},
        {"city": "NonExistentCity", "country": ""}  # Should fail gracefully
    ]

    for city_data in test_cities:
        try:
            query = json.dumps(city_data)
            result = agent._get_location_id(query)

            print(f"🔍 {city_data['city']}, {city_data['country']}:")

            try:
                parsed_result = json.loads(result)
                if parsed_result.get('status') == 'success':
                    print(f"   ✅ Dest ID: {parsed_result.get('dest_id')}")
                else:
                    print(f"   ❌ Failed: {result}")
            except json.JSONDecodeError:
                print(f"   ❌ Error: {result}")

        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")


def test_distance_enrichment():
    """Test distance calculation functionality"""
    print("\n🧪 Testing Distance Enrichment...")

    agent = BookingAgent()

    # Mock hotel data
    mock_hotels = [
        {
            "name": "Hotel Test 1",
            "price": 150.0,
            "coords": (52.2297, 21.0122)  # Warsaw coordinates
        },
        {
            "name": "Hotel Test 2",
            "price": 200.0,
            "coords": (52.2319, 21.0067)  # Slightly different Warsaw coordinates
        },
        {
            "name": "Hotel No Coords",
            "price": 100.0,
            "coords": None  # Should be filtered out
        }
    ]

    # Mock attractions data
    mock_attractions = [
        {
            "name": "Palace of Culture",
            "coords": (52.2316, 21.0067)
        },
        {
            "name": "Old Town",
            "coords": (52.2496, 21.0122)
        }
    ]

    try:
        enriched_hotels = agent.enrich_hotels_with_distances(mock_hotels, mock_attractions)

        print(f"✅ Enriched {len(enriched_hotels)} hotels with distance data")

        for hotel in enriched_hotels:
            print(f"\n🏨 {hotel['name']}:")
            print(f"   Distances: {hotel.get('distances_to_attractions', [])}")
            print(f"   Average: {hotel.get('avg_distance', 'N/A')} km")

    except Exception as e:
        print(f"❌ Distance calculation failed: {str(e)}")
        import traceback
        traceback.print_exc()


def test_api_tools_directly():
    """Test the individual tools directly"""
    print("\n🧪 Testing API Tools Directly...")

    agent = BookingAgent()

    # Test location ID tool
    print("🔧 Testing get_location_id tool...")
    location_result = agent._get_location_id('{"city": "Krakow", "country": "Poland"}')
    print(f"   Result: {location_result[:100]}...")

    # Test hotel search tool (if location ID worked)
    try:
        location_data = json.loads(location_result)
        if location_data.get('status') == 'success':
            print("🔧 Testing search_hotels_api tool...")

            search_params = {
                "city": "Krakow",
                "country": "Poland",
                "checkin_date": (date.today() + timedelta(days=14)).isoformat(),
                "checkout_date": (date.today() + timedelta(days=16)).isoformat(),
                "adults_number": 2,
                "room_number": 1,
                "currency": "PLN",
                "sort_by": "price"
            }

            search_result = agent._search_hotels_api(json.dumps(search_params))

            try:
                parsed_search = json.loads(search_result)
                if parsed_search.get('status') == 'success':
                    hotels_count = len(parsed_search.get('hotels', []))
                    print(f"   ✅ Found {hotels_count} hotels")
                else:
                    print(f"   ❌ Search failed: {parsed_search.get('message', 'Unknown')}")
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response: {search_result[:100]}...")

    except json.JSONDecodeError:
        print("   ❌ Could not parse location result, skipping hotel search test")


def main():
    """Run all tests"""
    print("🚀 Starting BookingAgent Tests\n")
    print("=" * 50)

    # Check if we have the required API keys
    try:
        from settings.config import config
        if not hasattr(config, 'BOOKING_API_KEY') or not config.BOOKING_API_KEY:
            print("❌ BOOKING_API_KEY not found in config!")
            print("   Make sure you have set up your API keys in settings/config.py")
            return
        else:
            print("✅ API keys found in config")
    except ImportError:
        print("❌ Could not import config!")
        print("   Make sure settings/config.py exists with your API keys")
        return

    print("=" * 50)

    # Run individual tests
    test_location_id_retrieval()
    test_api_tools_directly()
    test_distance_enrichment()
    test_basic_hotel_search()

    print("\n" + "=" * 50)
    print("🏁 Tests completed!")


if __name__ == "__main__":
    main()