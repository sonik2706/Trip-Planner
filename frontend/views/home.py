from typing import Dict
from datetime import date, timedelta
import streamlit as st

from frontend.models.travel_request import TravelRequest

def create_sidebar_filters():
    """Create sidebar with all planning options"""
    st.sidebar.header("🎯 Travel Planning Options")

    st.sidebar.subheader("📍 Destination")

    # --- City input
    city = st.sidebar.text_input("City", value="", help="Enter destination city")

    # --- Initialize session flags
    if "show_map_popup" not in st.session_state:
        st.session_state.show_map_popup = False
    if "confirmed_location" not in st.session_state:
        st.session_state.confirmed_location = None

    dest_data = None
    locations = []

    if city:
        try:
            hotel_filter = HotelFilter()
            locations = hotel_filter._get_raw_locations(city)

            if locations:
                # Wybór lokalizacji z listy
                options = [f"{l['label']} ({l['dest_type']})" for l in locations]
                selected_index = st.sidebar.selectbox(
                    "Select Location", list(range(len(options))),
                    format_func=lambda i: options[i]
                )

                # Automatyczne zatwierdzenie lokalizacji po wyborze
                dest_data = locations[selected_index]
                st.session_state.confirmed_location = dest_data

                # Pokazanie przycisku podglądu mapy
                if st.sidebar.button("📍 Preview on Map"):
                    st.session_state.show_map_popup = True

        except Exception as e:
            st.sidebar.error(f"Failed to fetch location: {e}")

    # --- Wyświetl mapkę w expanderze (pseudo-popup)
    if st.session_state.show_map_popup and st.session_state.confirmed_location:
        dest_data = st.session_state.confirmed_location
        lat = dest_data["latitude"]
        lon = dest_data["longitude"]

        with st.expander("📍 Location Preview", expanded=True):
            st.write(f"Selected: {dest_data['label']}")
            m = folium.Map(location=[lat, lon], zoom_start=13)
            folium.Marker([lat, lon], tooltip=dest_data["label"]).add_to(m)
            st_folium(m, use_container_width=True, height=500)

            if st.button("❌ Close preview"):
                st.session_state.show_map_popup = False
                st.rerun()

    # --- Final country/dest_id setup
    if st.session_state.confirmed_location:
        dest_data = st.session_state.confirmed_location
        country = dest_data.get("country", "")
        dest_id = dest_data.get("dest_id", None)
        dest_type = dest_data.get("dest_type", None)
        lat = dest_data["latitude"]
        lon = dest_data["longitude"]
    else:
        country = ""
        dest_id = None
        lat = lon = None

    # --- Show readonly field for country
    st.sidebar.text_input("Country (auto-detected)", value=country, disabled=True)

    # Dates
    st.sidebar.subheader("📅 Travel Dates")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        checkin = st.date_input("Check-in", value=date.today() + timedelta(days=30))
    with col2:
        checkout = st.date_input("Check-out", value=date.today() + timedelta(days=33))

    # Calculate and display trip duration
    trip_days = (checkout - checkin).days
    st.sidebar.info(f"🛏️ **Trip Duration:** {trip_days} day{'s' if trip_days != 1 else ''}")

    # Accommodation preferences
    st.sidebar.subheader("🏨 Accommodation")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        adults = st.number_input("Adults", 1, 10, 2)
    with col2:
        rooms = st.number_input("Rooms", 1, 5, 1)

    # Budget
    currency = st.sidebar.selectbox("Currency", ["USD", "EUR", "PLN", "GBP", "CAD"])

    budget_option = st.sidebar.radio(
        "Budget Type", ["Set Range", "Maximum Only", "No Limit"]
    )

    min_price, max_price = None, None
    if budget_option == "Set Range":
        price_range = st.sidebar.slider("Price Range per night", 0, 1000, (100, 300))
        min_price, max_price = price_range
    elif budget_option == "Maximum Only":
        max_price = st.sidebar.number_input("Maximum price per night", 0, 2000, 200)

    # Hotel preferences
    st.sidebar.subheader("⭐ Hotel Preferences")
    min_review = st.sidebar.slider("Minimum review score", 0.0, 10.0, 7.0, 0.5)

    star_options = st.sidebar.multiselect(
        "Star classes",
        [1, 2, 3, 4, 5],
        default=[3, 4, 5],
        help="Select preferred hotel star ratings",
    )

    max_hotels = st.sidebar.slider("Maximum hotels to show", 5, 20, 10)

    # Attractions
    st.sidebar.subheader("🎯 Attractions")
    num_attractions = st.sidebar.slider("Number of attractions", 3, 15, 8)

    attraction_focus = st.sidebar.text_input(
        "Focus/Theme (optional)",
        placeholder="e.g., history, art, food, nightlife",
        help="Specify what type of attractions you're interested in",
    )

    # Transportation
    st.sidebar.subheader("🚗 Transportation")
    travel_mode = st.sidebar.selectbox(
        "Preferred travel mode",
        ["transit", "walking", "driving"],
        help="How you plan to get around the city",
    )

    return TravelRequest(
        city=city,
        country=country,
        checkin_date=checkin.strftime("%Y-%m-%d"),
        checkout_date=checkout.strftime("%Y-%m-%d"),
        adults=adults,
        rooms=rooms,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        star_classes=star_options if star_options else None,
        min_review_score=min_review,
        max_hotels=max_hotels,
        num_attractions=num_attractions,
        attraction_focus=attraction_focus if attraction_focus else None,
        travel_mode=travel_mode,
        trip_days=trip_days,
    )

def display_home_screen():
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            """
        ### 🌟 Welcome to AI Travel Planner

        This intelligent travel planning system uses multiple specialized AI agents to create your perfect trip:

        **🎯 Attraction Agent**: Discovers the best attractions based on your interests and themes
        **🏨 Booking Agent**: Finds optimal hotels considering location, price, and value
        **🗺️ Map Agent**: Creates smart itineraries with optimized routes and timing
        **📍 Location Agent**: Provides precise coordinates and distance calculations

        ### 🚀 How to Use
        1. **Configure your preferences** in the sidebar (destination, dates, budget, etc.)
        2. **Click "Plan My Trip"** to start the AI planning process
        3. **Review your personalized plan** across multiple tabs
        4. **Export or share** your complete travel plan

        **👈 Start by filling out your preferences in the sidebar!**
        """
        )

    with col2:
        # Quick stats or tips
        st.markdown(
            """
        ### 📊 Planning Stats
        - **Multi-Agent AI** coordination
        - **Real-time** hotel and attraction data
        - **Optimized routing** with Google Maps
        - **Smart filtering** by budget and preferences
        - **Export options** for easy sharing

        ### 💡 Pro Tips
        - Use specific themes for attractions (e.g., "art", "food", "history")
        - Set realistic budgets for better recommendations
        - Consider travel mode for itinerary optimization
        - Save multiple plans for comparison
        """
        )

    # Feature highlights
    st.markdown("### ✨ Key Features")

    feature_col1, feature_col2, feature_col3 = st.columns(3)

    with feature_col1:
        st.markdown(
            """
        #### 🎯 Smart Discovery
        - AI-powered attraction finding
        - Customizable focus themes
        - Local insights and hidden gems
        - Coordinate-based recommendations
        """
        )

    with feature_col2:
        st.markdown(
            """
        #### 🏨 Intelligent Matching
        - Budget-aware recommendations
        - Location optimization scoring
        - Value analysis and ranking
        - Review-based filtering
        """
        )

    with feature_col3:
        st.markdown(
            """
        #### 🗺️ Route Optimization
        - Multi-day trip planning
        - Transportation mode optimization
        - Google Maps integration
        - Time and distance analysis
        """
        )