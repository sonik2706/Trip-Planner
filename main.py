import streamlit as st
import json
import requests
from datetime import date
import openai
import os
import time

from agents.attraction_agent import AttractionAgent
from agents.hotel_agent import HotelAgent
from agents.map_agent import MapAgent
from agents.prompt_agent import PromptAgent

DEFAULT_PARAMS = {
    "country": "Poland",
    "city": "Warsaw",
    "checkin_date": "2025-05-26",
    "checkout_date": "2025-05-27",
    "min_price": 50.0,
    "max_price": 50000.0,
    "room_number": 1,
    "adults_number": 2,
    "currency": "PLN",
    "stars": [3, 4, 5],
    "min_review_score": 0.0,
    "location_pref": "",
    "sort_by": "price",
    "max_hotels": 10,
}

with st.sidebar:
    st.header("Search Parameters")

    country = st.text_input("Country", DEFAULT_PARAMS["country"])
    city = st.text_input("City", DEFAULT_PARAMS["city"])
    checkin_date = st.date_input("Check-in Date", date.fromisoformat(DEFAULT_PARAMS["checkin_date"]))
    checkout_date = st.date_input("Check-out Date", date.fromisoformat(DEFAULT_PARAMS["checkout_date"]))
    min_price = st.number_input("Minimum Price", min_value=0.0, value=DEFAULT_PARAMS["min_price"])
    max_price = st.number_input("Maximum Price", min_value=0.0, value=DEFAULT_PARAMS["max_price"])
    room_number = st.number_input("Number of Rooms", min_value=1, value=DEFAULT_PARAMS["room_number"])
    adults_number = st.number_input("Number of Adults", min_value=1, value=DEFAULT_PARAMS["adults_number"])
    currency = st.selectbox("Currency", ["PLN", "EUR", "USD"], index=0)
    stars = st.multiselect("Hotel Star Rating", options=[1, 2, 3, 4, 5], default=DEFAULT_PARAMS["stars"])
    min_review_score = st.slider("Minimum Hotel Review Score", min_value=0.0, max_value=10.0, value=DEFAULT_PARAMS["min_review_score"], step=0.1)

    sort_by = st.selectbox(
        "Sort by",
        options=["price", "review_score", "shortest_distance"],
        format_func=lambda x: {
            "price": "Price",
            "review_score": "Review Score",
            "shortest_distance": "Closest to Attractions"
        }[x],
        index=0
    )
    max_hotels = st.number_input("Maximum Number of Hotels", min_value=1, value=DEFAULT_PARAMS["max_hotels"])

params = {
    "country": country,
    "city": city,
    "checkin_date": checkin_date.isoformat(),
    "checkout_date": checkout_date.isoformat(),
    "min_price": min_price,
    "max_price": max_price,
    "room_number": room_number,
    "adults_number": adults_number,
    "currency": currency,
    "stars": stars,
    "min_review_score": min_review_score,
    "sort_by": sort_by,
    "max_hotels": max_hotels,
}


# --- Streamlit UI ---
st.title("Trip Planner")
st.markdown("---")

user_description = st.text_area("Write your travel preferences or comments here")

hotel_agent = HotelAgent()

prompt_agent = PromptAgent()

# Initialize session_state for hotels if not set
if "hotels_data" not in st.session_state:
    st.session_state.hotels_data = []

if "attractions" not in st.session_state:
    st.session_state.attractions = []

if st.button("Run"):
    response = prompt_agent.extract(country ,city , user_description)
    st.write(response)

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🔍 Search Hotels"):
        if checkin_date >= checkout_date:
            st.error("Check-out date must be later than check-in date.")
            st.stop()

        with st.spinner("Fetching hotels..."):
            hotels = []
            try:
                hotels = hotel_agent.fetch_hotels_from_booking(params)
                st.session_state.hotels_data = hotels
            except Exception as e:
                st.error(e)

with col2:
    generate_disabled = not st.session_state.get("hotels_data")
    st.button("🧭 Generate Plan", disabled=generate_disabled)

    # with st.spinner("✅ Validating attraction locations using Nominatim..."):
    #     valid_attractions = hotel_agent.get_valid_locations_with_coords(st.session_state.attractions)

    # if not valid_attractions:
    #     st.warning("No valid attractions found.")
    # if not hotels:
    #     st.warning("No valid hotels found.")

    # enriched_hotels = hotel_agent.enrich_hotels_with_distances(hotels, valid_attractions)
    # enriched_hotels = [h for h in enriched_hotels if h.get("avg_distance") is not None]

    # # Sorting
    # if params["sort_by"] == "price":
    #     enriched_hotels = sorted(enriched_hotels, key=lambda x: x.get("price", float('inf')))
    # elif params["sort_by"] == "review_score":
    #     enriched_hotels = sorted(enriched_hotels, key=lambda x: x.get("review_score", 0), reverse=True)
    # elif params["sort_by"] == "shortest_distance":
    #     enriched_hotels = sorted(enriched_hotels, key=lambda x: x.get("avg_distance", float('inf')))

    # # Limit number of results
    # enriched_hotels = enriched_hotels[:params.get("max_hotels", 10)]

    # # Save to session_state
    # st.session_state.hotels_data = enriched_hotels
    # st.session_state.valid_attractions = valid_attractions

# Display hotel results if available
if st.session_state.hotels_data:
    st.subheader(f"Found Hotels in {params['city']}")
    for hotel in st.session_state.hotels_data:
        st.markdown("----")
        st.markdown(f"### 🏨 [{hotel['name']}]({hotel.get('link', '#')})")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"💰 **Price:** {hotel['price']} {params['currency']}")
            st.markdown(f"📍 **Address:** {hotel['location']}")
        with col2:
            st.markdown(f"⭐ **Review Score:** {hotel['review_score']}")
            if hotel.get("avg_distance") is not None:
                st.markdown(f"📏 **Avg. Distance to Attractions:** {hotel['avg_distance']:.2f} km")

        if hotel.get("distances_to_attractions") and st.session_state.valid_attractions:
            with st.expander("📌 Distances to Nearby Attractions"):
                for attr, dist in zip(st.session_state.valid_attractions, hotel["distances_to_attractions"]):
                    st.markdown(f"- **{attr['name']}**: {dist:.2f} km")


    # st.subheader("Tourist Attractions")
    # for attr in st.session_state.valid_attractions:
    #     st.markdown(f"- **{attr['name']}** — {attr['location']}")