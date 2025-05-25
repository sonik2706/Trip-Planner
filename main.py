import streamlit as st
import json
import requests
from datetime import date
import openai
import os
import time

from app.graph import Graph


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

hotel_params = {
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

user_description = st.text_area("Write your travel preferences or comments here...")

app = Graph()

# Initialize session_state for hotels if not set
if "trip_plan" not in st.session_state:
    st.session_state.trip_plan = []

if st.button("Run"):
    app.visualize_graph()
    st.info("Image saved!")
    # reponse = app.run(country, city, user_description, hotel_params)
    # st.write(response)
