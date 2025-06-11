import json
from typing import Dict
import folium
import streamlit as st
from streamlit_folium import st_folium

from backend.graph import Graph

from frontend.views.home import display_home_screen, create_sidebar_filters
from frontend.views.attractions import display_attractions
from frontend.views.hotels import display_hotels
from frontend.views.itinerary import display_itinerary
from frontend.models.travel_request import TravelRequest
from frontend.utils import load_css, format_graph_results

def initialize_session_state():
    """Initialize Streamlit session state"""
    if "travel_results" not in st.session_state:
        st.session_state.travel_results = None
    if "planning_stage" not in st.session_state:
        st.session_state.planning_stage = "input"
    if "manager" not in st.session_state:
        st.session_state.manager = None

def main():
    st.set_page_config(
        page_title="AI Travel Planner",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    load_css("frontend/assets/styles.css")

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

    # Get user inputs from sidebar
    travel_request = create_sidebar_filters()

    # Main planning button
    if st.sidebar.button("🚀 Plan My Trip", type="primary", use_container_width=True):
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

            with tab1:
                # display_summary_dashboard(results, travel_request)
                pass

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

            with tab5:
                # create_export_options(results, travel_request)
                pass

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
        display_home_screen()


if __name__ == "__main__":
    main()
