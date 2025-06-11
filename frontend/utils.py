from typing import Dict
import streamlit as st
from frontend.views.hotels import is_hotel_in_budget, get_budget_range_text
from frontend.models.travel_request import TravelRequest

def load_css(file):
    """Load CSS from a specified file and apply it to the Streamlit app.

    Args:
        file (str): The path to the CSS file.
    """
    with open(file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        
def format_graph_results(raw_results: Dict, travel_request: TravelRequest) -> Dict:
    """Format Graph results to match frontend expectations"""
    try:
        formatted = {
            "status": "success",
            "processing_time": 0.0
        }

        # Format attractions data
        if "attractions" in raw_results:
            attractions_data = raw_results["attractions"]

            # Handle both JSON string and dict
            if isinstance(attractions_data, str):
                attractions_data = json.loads(attractions_data)

            formatted["attractions"] = {
                "city": attractions_data.get("city", travel_request.city),
                "focus": attractions_data.get("focus", travel_request.attraction_focus or "general"),
                "attractions": attractions_data.get("attractions", [])
            }

        # Format hotels data
        if "hotels" in raw_results:
            hotels_data = raw_results["hotels"]

            # Handle both JSON string and dict
            if isinstance(hotels_data, str):
                hotels_data = json.loads(hotels_data)

            # PROBLEM 8: Popraw zbieranie wszystkich hoteli i dodaj brakujące pola
            all_hotels = []
            for category in hotels_data.get("categories", []):
                for hotel in category.get("hotels", []):
                    # Convert hotel format to frontend expected format
                    formatted_hotel = {
                        "name": hotel.get("name", "Unknown Hotel"),
                        "location": hotels_data.get("city", travel_request.city),
                        "price": hotel.get("price", 0),
                        "currency": hotel.get("currency", travel_request.currency),
                        "review_score": hotel.get("review_score", 0),
                        "review_count": hotel.get("review_count", 0),
                        "star_class": hotel.get("stars", 3),
                        "distance_to_attractions": hotel.get("average_distance_km", 0),
                        "ranking_score": hotel.get("value_score", 0.5),
                        "value_score": hotel.get("value_score", 0.5),
                        "link": hotel.get("link", ""),
                        "category": category.get("name", "Recommended"),
                        "why_recommended": hotel.get("why_recommended", "Good option"),
                        "in_original_budget": is_hotel_in_budget(hotel, travel_request),
                        # PROBLEM 9: Dodaj brakujące pola dla map i analiz
                        "average_distance_km": hotel.get("average_distance_km", 1.0)
                    }
                    all_hotels.append(formatted_hotel)

            # Calculate statistics
            budget_hotels = [h for h in all_hotels if h["in_original_budget"]]
            alternative_hotels = [h for h in all_hotels if not h["in_original_budget"]]

            # PROBLEM 10: Zabezpiecz przed dzieleniem przez zero
            avg_price = 0
            if all_hotels:
                prices = [h["price"] for h in all_hotels if h["price"] > 0]
                if prices:
                    avg_price = round(sum(prices) / len(prices), 2)
            
            formatted["hotels"] = {
                "total_found": len(all_hotels),
                "budget_hotels_count": len(budget_hotels),
                "alternative_hotels_count": len(alternative_hotels),
                "categories": hotels_data.get("categories", []),
                "pro_tips": hotels_data.get("pro_tips", []),
                "avg_price": avg_price,
                # PROBLEM 11: Dodaj all_hotels do wyników
                "all_hotels": all_hotels
            }

        if "itinerary" in raw_results:
            formatted["itinerary"] = raw_results["itinerary"]

        # Add summary
        formatted["summary"] = {
            "total_attractions": len(formatted.get("attractions", {}).get("attractions", [])),
            "total_hotels": formatted.get("hotels", {}).get("total_found", 0),
            "budget_hotels_count": formatted.get("hotels", {}).get("budget_hotels_count", 0),
            "duration": f"{travel_request.trip_days} days",
            "budget_range": get_budget_range_text(travel_request)
        }

        return formatted

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to format results: {str(e)}",
            "raw_data": raw_results
        }