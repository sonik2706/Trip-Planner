from typing import Dict
from frontend.models.travel_request import TravelRequest

def is_hotel_in_budget(hotel: Dict, travel_request: TravelRequest) -> bool:
    """Check if hotel is within budget"""
    price = hotel.get("price", 0)

    if travel_request.min_price and price < travel_request.min_price:
        return False
    if travel_request.max_price and price > travel_request.max_price:
        return False

    return True


def get_budget_range_text(travel_request: TravelRequest) -> str:
    """Get budget range as text"""
    if travel_request.min_price and travel_request.max_price:
        return f"{travel_request.min_price}-{travel_request.max_price} {travel_request.currency}"
    elif travel_request.max_price:
        return f"Up to {travel_request.max_price} {travel_request.currency}"
    elif travel_request.min_price:
        return f"From {travel_request.min_price} {travel_request.currency}"
    else:
        return "Not specified"