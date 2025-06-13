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
from frontend.views.export import create_export_options
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

def handle_node_update(node_name, node_output, status_text, progress_bar):
    """Handle individual node updates during graph execution"""
    if node_name == "verify_prompt":
        status_text.text("🎯 Finding attractions...")
        progress_bar.progress(25)
        return node_output
        
    elif node_name == "search_for_attractions":
        status_text.text("🏨 Finding hotels...")
        progress_bar.progress(50)
        return node_output
        
    elif node_name == "find_hotels":
        status_text.text("⏳ Hotels found, waiting for selection...")
        progress_bar.progress(75)
        return node_output
    
    return node_output

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
        selected_hotel_idx = None
        
        for idx, hotel in enumerate(hotels):
            with st.container():
                # Display hotel card with error handling
                try:
                    display_hotel_card(hotel, st.session_state.travel_request)
                except Exception as card_error:
                    st.error(f"Error displaying hotel {idx + 1}: {card_error}")
                    # Show basic hotel info as fallback
                    st.write(f"**Hotel {idx + 1}**: {hotel.get('name', 'Unknown')}")
                    if 'price' in hotel:
                        st.write(f"Price: {hotel['price']}")
                
                # Add select button directly under each hotel card
                if st.button(f"Select Hotel {idx + 1}", key=f"select_hotel_{idx}", type="primary", use_container_width=True): 
                    selected_hotel_idx = idx
                
                st.markdown("---")  # Add separator between hotels
        
        # Process hotel selection
        if selected_hotel_idx is not None:
            selected_hotel = hotels[selected_hotel_idx]
            
            with st.spinner("🏨 Continuing with selected hotel..."):
                try:
                    # Create new state with selected hotel
                    continued_state = st.session_state.graph_state.copy()
                    continued_state["selected_hotel"] = selected_hotel
                    
                    # Create a new graph instance for the remaining steps
                    app_continue = Graph()
                    
                    # Since we can't resume from interrupt without checkpointer,
                    # we'll manually run the remaining nodes
                    try:
                        # Run wait_for_hotel_selection node manually
                        after_hotel_selection = app_continue._wait_for_hotel_selection(continued_state)
                        
                        status_text = st.empty()
                        status_text.text("🗓️ Building itinerary...")
                        
                        # Run build_itinerary node manually  
                        final_state = app_continue._build_itinerary(after_hotel_selection)
                        
                        status_text.text("✅ Itinerary complete!")
                        
                    except Exception as manual_error:
                        st.error(f"Manual execution failed: {manual_error}")
                        
                        # Last resort - try full re-run with selected hotel in initial state
                        initial_with_hotel = {
                            "country": st.session_state.travel_request.country,
                            "city": st.session_state.travel_request.city, 
                            "context": "",
                            "num_attractions": st.session_state.travel_request.num_attractions,
                            "hotel_params": continued_state["hotel_params"],
                            "focus": st.session_state.travel_request.attraction_focus,
                            "selected_hotel": selected_hotel
                        }
                        
                        # Use simple graph without interrupts
                        simple_graph = app_continue._raw_graph.compile()
                        final_state = simple_graph.invoke(initial_with_hotel)
                    
                    # Format results for frontend
                    try:
                        formatted_results = format_graph_results(final_state, st.session_state.travel_request)
                        
                        # Check if format_graph_results actually failed internally
                        if isinstance(formatted_results, dict) and formatted_results.get("status") != "success":
                            raise Exception(f"format_graph_results failed: {formatted_results.get('error_message')}")
                        
                    except Exception as format_error:
                        st.error(f"ERROR in format_graph_results: {format_error}")
                        
                        # Create a manual formatted result to bypass the error
                        formatted_results = {
                            "status": "success",
                            "attractions": final_state.get("attractions", {}).get("attractions", []),
                            "hotels": [final_state.get("selected_hotel", {})],
                            "itinerary": final_state.get("itinerary", {}),
                            "request": {
                                "city": final_state.get("city", ""),
                                "country": final_state.get("country", ""),
                                "focus": final_state.get("focus", "")
                            }
                        }
                        st.warning("Used fallback formatting due to error in format_graph_results")
                    
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
                    
                    # Stream through the graph execution until we find hotels
                    current_state = None
                    hotels_found = False
                    
                    try:
                        # Don't use thread_id config since graph doesn't have checkpointer
                        for event in app.graph.stream(initial_state):
                            # Handle different event formats
                            if isinstance(event, dict):
                                # event is a dictionary containing node updates
                                for node_name, node_output in event.items():
                                    current_state = handle_node_update(node_name, node_output, status_text, progress_bar)
                                    
                                    # Stop after hotels are found (before the interrupt node)
                                    if node_name == "find_hotels" and "hotels" in node_output:
                                        hotels_found = True
                                        current_state = node_output
                                        break
                                        
                            elif isinstance(event, tuple) and len(event) == 2:
                                # event is a tuple (node_name, node_output)
                                node_name, node_output = event
                                current_state = handle_node_update(node_name, node_output, status_text, progress_bar)
                                
                                if node_name == "find_hotels" and isinstance(node_output, dict) and "hotels" in node_output:
                                    hotels_found = True
                                    current_state = node_output
                                    break
                                    
                            else:
                                # Unexpected format - continue processing
                                continue
                            
                            # Break if we found hotels
                            if hotels_found:
                                break
                                
                    except Exception as stream_error:
                        st.error(f"Error during streaming: {stream_error}")
                        st.write(f"Stream error details: {type(stream_error)}")
                        
                        # Try a different approach - run the graph step by step manually
                        try:
                            # Create a simple version without interrupts
                            app_simple = Graph()
                            # Get the raw graph without compilation
                            simple_graph = app_simple._raw_graph.compile()  # Compile without interrupt
                            
                            # Run until we get hotels
                            current_state = simple_graph.invoke(initial_state)
                            if "hotels" in current_state:
                                hotels_found = True
                            
                        except Exception as fallback_error:
                            st.error(f"Fallback also failed: {fallback_error}")
                            return

                    progress_bar.progress(75)
                    status_text.text("⏳ Waiting for hotel selection...")

                    # Save the current state for hotel selection
                    if hotels_found and current_state and isinstance(current_state, dict) and "hotels" in current_state:
                        st.session_state.graph_state = current_state
                        st.session_state.compiled_graph = app.graph
                        st.session_state.planning_stage = "hotel_selection"

                        progress_bar.progress(100)
                        status_text.text("✅ Ready for hotel selection!")

                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()

                        st.success("🏨 Hotels found! Please select your preferred hotel.")
                        st.rerun()
                    else:
                        st.error("❌ No hotels found in the graph execution. Please check your criteria.")
                        
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
                tab1, tab2, tab3, tab4 = st.tabs(
                    [
                        "🎯 Attractions",
                        "🏨 Hotels",
                        "🗓️ Itinerary",
                        "📤 Export",
                    ]
                )

                with tab1:
                    if results.get("attractions"):
                        display_attractions(results["attractions"])
                    else:
                        st.warning("No attraction data available")

                with tab2:
                    if results.get("hotels"):
                        display_hotels(results["hotels"], st.session_state.travel_request.currency, st.session_state.travel_request)
                    else:
                        st.warning("No hotel data available")

                with tab3:
                    if results.get("itinerary"):
                        display_itinerary(results["itinerary"])
                    else:
                        st.warning("No itinerary data available")

                with tab4:
                    create_export_options(results, st.session_state.travel_request)
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
                    st.write("**Error Message:**")
                    st.write(error_msg)
                    st.write("**Full Results:**") 
                    st.json(results)

                # Retry button
                if st.button("🔄 Try Again"):
                    reset_session_state()
                    st.rerun()
        else:
            st.warning("No travel results available")
        
        # Add plan new trip button
        if st.sidebar.button("🆕 Plan New Trip", use_container_width=True):
            reset_session_state()
            st.rerun()


if __name__ == "__main__":
    main()