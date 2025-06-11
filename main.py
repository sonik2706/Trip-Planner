#!/usr/bin/env python3
"""
Test script for BookingAgent
Run this to test the BookingAgent independently
"""

import json
from typing import Dict
import folium
import streamlit as st
from streamlit_folium import st_folium

from backend.graph import Graph

from frontend.views.home import display_home_screen, create_sidebar_filters
from frontend.views.attractions import display_attractions
from frontend.views.hotels import display_hotels, display_hotel_card
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
    if "graph_state" not in st.session_state:
        st.session_state.graph_state = None
    if "compiled_graph" not in st.session_state:
        st.session_state.compiled_graph = None
    if "travel_request" not in st.session_state:
        st.session_state.travel_request = None

def display_hotel_selection():
    """Display hotel selection interface"""
    st.markdown(
        """
    <div class="main-header">
        <h2>🏨 Choose Your Hotel</h2>
        <p>Select the hotel that best fits your preferences</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    if "hotels" in st.session_state.graph_state:
        hotels = st.session_state.graph_state["hotels"]
        
        if not hotels:
            st.error("No hotels found. Please try again with different criteria.")
            if st.button("🔄 Start Over"):
                reset_session_state()
                st.rerun()
            return
        
        st.write(f"Found **{len(hotels)}** hotels matching your criteria:")
        
        # Create hotel selection cards
        cols = st.columns(min(3, len(hotels)))
        selected_hotel_idx = None
        
        for idx, hotel in enumerate(hotels):
            display_hotel_card(hotel, st.session_state.travel_request)
            if st.button(f"Select This Hotel", key=f"select_hotel_{idx}", type="primary"): 
                selected_hotel_idx = idx
        
        # Process hotel selection
        if selected_hotel_idx is not None:
            selected_hotel = hotels[selected_hotel_idx]
            
            with st.spinner("🏨 Continuing with selected hotel..."):
                try:
                    # Update state with selected hotel
                    updated_state = st.session_state.graph_state.copy()
                    updated_state["selected_hotel"] = selected_hotel
                    
                    # Resume graph execution
                    final_result = st.session_state.compiled_graph.invoke(
                        updated_state,
                        config={"configurable": {"thread_id": "user_session"}}
                    )
                    
                    # Format results for frontend
                    formatted_results = format_graph_results(final_result, st.session_state.travel_request)
                    
                    # Save final results and move to results stage
                    st.session_state.travel_results = formatted_results
                    st.session_state.planning_stage = "results"
                    
                    # Clean up intermediate states
                    st.session_state.graph_state = None
                    st.session_state.compiled_graph = None
                    
                    st.success(f"✅ Selected: {selected_hotel.get('name', 'Hotel')}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Failed to continue planning: {str(e)}")
                    if st.checkbox("Show error details"):
                        st.exception(e)
    else:
        st.error("No hotel data available. Please start over.")
        if st.button("🔄 Start Over"):
            reset_session_state()
            st.rerun()

def reset_session_state():
    """Reset all session state variables"""
    keys_to_reset = ["travel_results", "planning_stage", "manager", "graph_state", 
                     "compiled_graph", "travel_request"]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reset to initial state
    st.session_state.planning_stage = "input"

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
    
    # Handle different planning stages
    if st.session_state.planning_stage == "input":
        # Show sidebar and get user inputs
        travel_request = create_sidebar_filters()
        st.session_state.travel_request = travel_request  # Save for later use
        
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
                    # Initialize and compile the graph
                    app = Graph()
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text("Verifying prompt...")
                    initial_state = {
                        "country": hotel_params["country"],
                        "city": hotel_params["city"],
                        "context": context,
                        "num_attractions": travel_request.num_attractions,
                        "hotel_params": hotel_params,
                        "focus": travel_request.attraction_focus
                    }
                    for mode, step in app.graph.stream(initial_state, stream_mode=['updates']):
                        if "verify_prompt" in step.keys():
                            status_text.text("🎯 Finding attractions...")
                            progress_bar.progress(10)

                        if "search_for_attractions" in step.keys():
                            status_text.text("🏨 Finding hotels...")
                            progress_bar.progress(25)

                        elif "find_hotels" in step.keys():
                            status_text.text("waiting...")
                            progress_bar.progress(50)

                            # Save graph state and break
                            last_checkpoint = step.checkpoint
                            partial_state = step.state
                            break

                    progress_bar.progress(75)
                    status_text.text("⏳ Waiting for hotel selection...")

                    # Save the interrupted state
                    st.session_state.graph_state = state
                    st.session_state.compiled_graph = app.graph
                    st.session_state.planning_stage = "hotel_selection"

                    progress_bar.progress(100)
                    status_text.text("✅ Ready for hotel selection!")

                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()

                    st.success("🏨 Hotels found! Please select your preferred hotel.")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Planning failed: {str(e)}")
                    if st.checkbox("Show error details"):
                        st.exception(e)

        # Show welcome screen when no results
        if not st.session_state.travel_results and st.session_state.planning_stage == "input":
            display_home_screen()
    
    elif st.session_state.planning_stage == "hotel_selection":
        # Display hotel selection interface
        display_hotel_selection()
        
        # Add back button
        if st.sidebar.button("⬅️ Back to Planning", use_container_width=True):
            reset_session_state()
            st.rerun()
    
    elif st.session_state.planning_stage == "results":
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
                        display_hotels(results["hotels"], st.session_state.travel_request.currency, st.session_state.travel_request)
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
                    reset_session_state()
                    st.rerun()
        
        # Add plan new trip button
        if st.sidebar.button("🆕 Plan New Trip", use_container_width=True):
            reset_session_state()
            st.rerun()


if __name__ == "__main__":
    main()