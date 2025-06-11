import json
from typing import Dict
from datetime import date, timedelta
import folium
import streamlit as st
from streamlit_folium import st_folium

from backend.graph import Graph
from backend.agents.utils.hotel_filter import HotelFilter
from frontend.models.travel_request import TravelRequest
from frontend.views.attractions import display_attractions
from frontend.views.hotels import display_hotels
from frontend.views.itinerary import display_itinerary
from frontend.utils import is_hotel_in_budget, get_budget_range_text

def initialize_session_state():
    """Initialize Streamlit session state"""
    if "travel_results" not in st.session_state:
        st.session_state.travel_results = None
    if "planning_stage" not in st.session_state:
        st.session_state.planning_stage = "input"
    if "manager" not in st.session_state:
        st.session_state.manager = None


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

def main():
    st.set_page_config(
        page_title="AI Travel Planner",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better styling
    st.markdown(
        """
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1e3c72;
    }
    .status-success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .status-error {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Header
    st.markdown(
        """
    <div class="main-header">
        <h1>✈️ AI-Powered Travel Planner</h1>
        <p>Intelligent recommendations for attractions, hotels, and itineraries using multiple AI agents</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    initialize_session_state()

    app = Graph()
    app.visualize_graph()
    # Show agent status

    # Get user inputs from sidebar
    travel_request = create_sidebar_filters()

    # Main planning button
    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("🚀 Plan My Trip", type="primary", use_container_width=True):
            st.session_state.show_map_popup = False
            hotel_params = {
                "country": travel_request.country,
                "city": travel_request.city,
                "checkin_date": travel_request.checkin_date,
                "checkout_date": travel_request.checkout_date,
                "min_price": travel_request.min_price,
                "max_price": travel_request.max_price,
                "room_number": travel_request.rooms,
                "adults_number": travel_request.adults,
                "currency": travel_request.currency,
                "stars": travel_request.star_classes,
                "min_review_score": travel_request.min_review_score,
                "max_hotels": travel_request.max_hotels,
            }

            context = ""

            with st.spinner("🤖 AI agents are working on your travel plan..."):
                try:
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    status_text.text("🎯 Finding attractions...")
                    progress_bar.progress(25)

                    # Run the graph and get results
                    raw_results = app.run(context, hotel_params, travel_request.attraction_focus, travel_request.num_attractions)

                    st.write("DEBUG: Raw results from Graph:")
                    st.json(raw_results)  # Debug - pokaż surowe wyniki

                    progress_bar.progress(75)
                    status_text.text("🏨 Finding hotels...")

                    # Format results for frontend
                    formatted_results = format_graph_results(raw_results, travel_request)
                    st.write("DEBUG: Formatted results:")
                    st.json(formatted_results)  # Debug - pokaż sformatowane wyniki

                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")

                    # Save to session state
                    st.session_state.travel_results = formatted_results
                    st.session_state.planning_stage = "results"

                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()

                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Planning failed: {str(e)}")
                    if st.checkbox("Show error details"):
                        st.exception(e)

    with col2:
        if st.button("🔍 Preview", use_container_width=True):
            st.info("📋 Request Preview")
            with st.expander("See planning details", expanded=True):
                st.json(travel_request.__dict__)

    # Display results
    if st.session_state.travel_results:
        results = st.session_state.travel_results

        if results.get("status") == "success":
            # Success notification
            st.markdown(
                '<div class="status-success">✅ Your comprehensive travel plan is ready!</div>',
                unsafe_allow_html=True,
            )
            st.balloons()  # Celebratory animation

            # Create main tabs for results
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                [
                    "📋 Dashboard",
                    "🎯 Attractions",
                    "🏨 Hotels",
                    "🗓️ Itinerary",
                    "📤 Export",
                ]
            )

            # with tab1:
            #     display_summary_dashboard(results, travel_request)

            with tab2:
                if results.get("attractions"):
                    display_attractions(results["attractions"])
                else:
                    st.warning("No attraction data available")

            with tab3:
                if results.get("hotels"):
                    display_hotels(results["hotels"], travel_request.currency, travel_request)
                else:
                    st.warning("No hotel data available")

            with tab4:
                if results.get("itinerary"):
                    display_itinerary(results["itinerary"])
                else:
                    st.warning("No itinerary data available")

            # with tab5:
            #     create_export_options(results, travel_request)

        else:
            # Error display
            error_msg = results.get(
                "error_message", results.get("message", "Unknown error")
            )
            st.markdown(
                f'<div class="status-error">❌ Planning failed: {error_msg}</div>',
                unsafe_allow_html=True,
            )

            # Show request details for debugging
            with st.expander("🔍 Request Details (for debugging)"):
                st.json(results.get("request", {}))

            # Retry button
            if st.button("🔄 Try Again"):
                st.session_state.travel_results = None
                st.rerun()

    else:
        # Welcome screen
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


if __name__ == "__main__":
    main()
