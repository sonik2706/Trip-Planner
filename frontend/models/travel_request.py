from typing import List, Optional
from dataclasses import dataclass

@dataclass
class TravelRequest:
    """Fallback data class for travel planning request"""

    city: str
    country: str = ""
    checkin_date: str = ""
    checkout_date: str = ""
    adults: int = 2
    rooms: int = 1
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "USD"
    star_classes: List[int] = None
    min_review_score: float = 7.0
    max_hotels: int = 10
    num_attractions: int = 5
    attraction_focus: Optional[str] = None
    travel_mode: str = "transit"
    trip_days: int = 3
    dest_id: Optional[str] = None
    dest_type: Optional[str] = None
