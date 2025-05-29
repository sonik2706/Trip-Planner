import streamlit as st
import json
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
import logging

from app.graph import Graph


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

    # Basic trip info
    st.sidebar.subheader("📍 Destination")
    city = st.sidebar.text_input("City", value="Krakow", help="Enter destination city")
    country = st.sidebar.text_input("Country (optional)", value="Poland")

    # Dates
    st.sidebar.subheader("📅 Travel Dates")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        checkin = st.date_input("Check-in", value=date.today() + timedelta(days=30))
    with col2:
        checkout = st.date_input("Check-out", value=date.today() + timedelta(days=33))

    trip_days = st.sidebar.slider("Trip duration (days)", 1, 14, 3)

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


def display_attractions(attractions_data: Dict):
    """Display attractions results"""
    st.subheader(f"🎯 Top Attractions in {attractions_data['city']}")

    if attractions_data.get("focus") and attractions_data["focus"] != "general":
        st.info(f"🎨 Focused on: **{attractions_data['focus']}**")

    attractions = attractions_data.get("attractions", [])
    if not attractions:
        st.warning("No attractions found")
        return

    # Create columns for attractions
    cols = st.columns(2)
    for i, attraction in enumerate(attractions):
        with cols[i % 2]:
            with st.container():
                st.markdown(f"**📍 {attraction.get('name', 'Unknown')}**")
                st.write(attraction.get("description", "No description available"))

                # Show coordinates if available
                if attraction.get("coords"):
                    coords = attraction["coords"]
                    st.caption(f"📍 Location: {coords[0]:.4f}, {coords[1]:.4f}")

                if attraction.get("fun_facts"):
                    st.caption(f"💡 {attraction['fun_facts']}")
                st.markdown("---")

    # Map visualization for attractions with coordinates
    attractions_with_coords = [a for a in attractions if a.get("coords")]
    if attractions_with_coords:
        st.subheader("🗺️ Attractions Map")

        map_data = pd.DataFrame(
            {
                "name": [a["name"] for a in attractions_with_coords],
                "lat": [a["coords"][0] for a in attractions_with_coords],
                "lon": [a["coords"][1] for a in attractions_with_coords],
                "description": [
                    a.get("description", "")[:100] + "..."
                    for a in attractions_with_coords
                ],
            }
        )

        st.map(map_data[["lat", "lon"]], zoom=12)

        # Attraction details table
        st.dataframe(
            map_data[["name", "description"]], use_container_width=True, hide_index=True
        )


def display_hotels(hotels_data: Dict, currency: str):
    """Display hotel recommendations with enhanced visualization"""
    st.subheader("🏨 Hotel Recommendations")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Hotels", hotels_data["total_found"])
    with col2:
        st.metric("In Budget", hotels_data["budget_hotels_count"])
    with col3:
        st.metric("Alternatives", hotels_data["alternative_hotels_count"])
    with col4:
        avg_price = sum(h["price"] for h in hotels_data["hotels"][:5]) / min(
            5, len(hotels_data["hotels"])
        )
        st.metric("Avg Price", f"{avg_price:.0f} {currency}")

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(
        ["🏆 Top Recommendations", "📊 Price Analysis", "🗺️ Location Map"]
    )

    with tab1:
        # Display hotels in categories
        budget_hotels = [h for h in hotels_data["hotels"] if h["in_original_budget"]]
        alternative_hotels = [
            h for h in hotels_data["hotels"] if not h["in_original_budget"]
        ]

        if budget_hotels:
            st.markdown("### 💰 Hotels Within Budget")
            for hotel in budget_hotels[:5]:
                display_hotel_card(hotel)

        if alternative_hotels:
            st.markdown("### 🔄 Alternative Options")
            st.info("These hotels exceed your budget but offer excellent value")
            for hotel in alternative_hotels[:3]:
                display_hotel_card(hotel)

    with tab2:
        # Price analysis chart
        if hotels_data["hotels"]:
            df = pd.DataFrame(hotels_data["hotels"])

            fig = px.scatter(
                df,
                x="price",
                y="review_score",
                size="value_score",
                color="star_class",
                hover_data=["name", "distance_to_attractions"],
                title="Hotel Price vs Quality Analysis",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Mock map (replace with real coordinates when available)
        st.info(
            "🗺️ Map visualization would show hotel locations relative to attractions"
        )
        if hotels_data["hotels"]:
            map_data = pd.DataFrame(
                {
                    "name": [h["name"] for h in hotels_data["hotels"][:5]],
                    "lat": [50.0647 + i * 0.001 for i in range(5)],
                    "lon": [19.9450 + i * 0.001 for i in range(5)],
                    "price": [h["price"] for h in hotels_data["hotels"][:5]],
                }
            )
            st.map(map_data[["lat", "lon"]], zoom=13)


def display_hotel_card(hotel: Dict):
    """Display individual hotel card"""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"**🏨 {hotel['name']}**")
            st.write(f"📍 {hotel['location']}")
            st.caption(
                f"⭐ {hotel['review_score']}/10 ({hotel['review_count']} reviews)"
            )

        with col2:
            st.metric("Price/night", f"{hotel['price']} {hotel['currency']}")
            st.write(f"🏃 {hotel['distance_to_attractions']:.1f}km to attractions")

        with col3:
            st.write(f"{'⭐' * hotel['star_class']}")
            st.markdown(f"[Book Now]({hotel['link']})")

        # Progress bars for scores
        col1, col2 = st.columns(2)
        with col1:
            st.progress(
                hotel["ranking_score"], text=f"Ranking: {hotel['ranking_score']:.2f}"
            )
        with col2:
            st.progress(hotel["value_score"], text=f"Value: {hotel['value_score']:.2f}")

        if not hotel["in_original_budget"]:
            st.warning(f"💡 {hotel['category']}: Exceeds budget but high quality")

        st.markdown("---")


def display_itinerary(itinerary_data: Dict):
    """Display optimized itinerary"""
    st.subheader(
        f"🗓️ {itinerary_data.get('days', 'Multi')}-Day Itinerary for {itinerary_data.get('city', 'Your Destination')}"
    )

    # Itinerary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Travel Mode", itinerary_data.get("travel_mode", "Transit").title())
    with col2:
        st.metric(
            "Total Distance", itinerary_data.get("total_distance", "Calculating...")
        )
    with col3:
        st.metric(
            "Estimated Time", itinerary_data.get("estimated_time", "Calculating...")
        )

    # Display daily itinerary
    itinerary = itinerary_data.get("itinerary", {})
    if isinstance(itinerary, dict):
        for day, activities in itinerary.items():
            with st.expander(f"📅 {day}", expanded=True):
                if isinstance(activities, list):
                    for activity in activities:
                        st.write(f"• {activity}")
                else:
                    st.write(activities)
    elif isinstance(itinerary, str):
        # Handle string result from agent
        st.write(itinerary)
    else:
        st.info("Itinerary optimization in progress...")

    # Maps link
    maps_link = itinerary_data.get("maps_link")
    if maps_link:
        st.markdown(f"🗺️ [Open Optimized Route in Google Maps]({maps_link})")

    # Additional itinerary insights
    if itinerary_data.get("accommodation"):
        st.info(f"🏨 **Base Accommodation**: {itinerary_data['accommodation']}")


def display_summary_dashboard(results: Dict, request: TravelRequest):
    """Display comprehensive summary dashboard"""
    st.subheader("📋 Travel Plan Dashboard")

    summary = results.get("summary", {})

    # Key metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Attractions",
            summary.get("total_attractions", 0),
            delta=f"Focus: {request.attraction_focus or 'General'}",
        )

    with col2:
        st.metric(
            "Hotels Found",
            summary.get("total_hotels", 0),
            delta=f"{summary.get('budget_hotels_count', 0)} in budget",
        )

    with col3:
        st.metric(
            "Trip Duration",
            summary.get("duration", f"{request.trip_days} days"),
            delta=f"{request.travel_mode.title()} focused",
        )

    with col4:
        budget_range = summary.get("budget_range", "Not specified")
        st.metric(
            "Budget Range",
            budget_range.split(" ")[0] if budget_range != "Not specified" else "Any",
        )
        st.caption(f"Currency: {request.currency}")

    with col5:
        processing_time = results.get("processing_time")
        if processing_time:
            st.metric("Processing Time", f"{processing_time:.1f}s")
        else:
            st.metric("Status", "✅ Complete")

    # Planning overview
    st.markdown("### 🎯 Planning Overview")

    overview_col1, overview_col2 = st.columns(2)

    with overview_col1:
        st.markdown("**📍 Destination Details**")
        st.write(f"• **City**: {request.city}")
        if request.country:
            st.write(f"• **Country**: {request.country}")
        st.write(f"• **Dates**: {request.checkin_date} to {request.checkout_date}")
        st.write(
            f"• **Travelers**: {request.adults} adult{'s' if request.adults != 1 else ''}"
        )
        st.write(f"• **Rooms**: {request.rooms}")

    with overview_col2:
        st.markdown("**⚙️ Planning Preferences**")
        st.write(f"• **Min Review Score**: {request.min_review_score}/10")
        if request.star_classes:
            st.write(f"• **Star Classes**: {', '.join(map(str, request.star_classes))}")
        else:
            st.write("• **Star Classes**: Any")
        st.write(f"• **Travel Mode**: {request.travel_mode.title()}")
        if request.attraction_focus:
            st.write(f"• **Attraction Focus**: {request.attraction_focus}")

    # Budget analysis
    if summary.get("estimated_budget"):
        st.markdown("### 💰 Budget Estimation")
        st.info(f"💡 **Estimated Total Cost**: {summary['estimated_budget']}")
        st.caption(
            "*Includes accommodation and estimated extras (food, transport, activities)"
        )


def create_export_options(results: Dict, request: TravelRequest):
    """Create export and sharing options"""
    st.subheader("📤 Export & Share")

    col1, col2, col3 = st.columns(3)

    with col1:
        # JSON export
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        st.download_button(
            label="📄 Download JSON",
            data=json_data,
            file_name=f"travel_plan_{request.city}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        # CSV export for hotels
        if results.get("hotels", {}).get("hotels"):
            hotels_df = pd.DataFrame(results["hotels"]["hotels"])
            csv_data = hotels_df.to_csv(index=False)
            st.download_button(
                label="🏨 Hotels CSV",
                data=csv_data,
                file_name=f"hotels_{request.city}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col3:
        # Text summary export
        summary_text = create_text_summary(results, request)
        st.download_button(
            label="📝 Text Summary",
            data=summary_text,
            file_name=f"travel_summary_{request.city}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # Sharing options
    st.markdown("### 🔗 Quick Actions")
    sharing_col1, sharing_col2, sharing_col3 = st.columns(3)

    with sharing_col1:
        if st.button("📧 Email Plan", use_container_width=True):
            st.info(
                "💡 **Email Integration**: You can copy the text summary above and email it, or integrate with your email service."
            )

    with sharing_col2:
        if st.button("📱 Mobile Share", use_container_width=True):
            st.info(
                "💡 **Mobile Sharing**: Access this page on mobile to share via your preferred messaging app."
            )

    with sharing_col3:
        if st.button("🔄 Plan Again", use_container_width=True):
            st.session_state.travel_results = None
            st.session_state.planning_stage = "input"
            st.rerun()


def create_text_summary(results: Dict, request: TravelRequest) -> str:
    """Create a text summary of the travel plan"""
    lines = []
    lines.append(f"✈️ TRAVEL PLAN FOR {request.city.upper()}")
    lines.append("=" * 50)
    lines.append("")

    # Basic info
    lines.append("📋 TRIP DETAILS")
    lines.append(f"Destination: {request.city}, {request.country}")
    lines.append(f"Dates: {request.checkin_date} to {request.checkout_date}")
    lines.append(f"Duration: {request.trip_days} days")
    lines.append(f"Travelers: {request.adults} adult(s), {request.rooms} room(s)")
    lines.append("")

    # Attractions
    attractions = results.get("attractions", {}).get("attractions", [])
    if attractions:
        lines.append("🎯 TOP ATTRACTIONS")
        for i, attr in enumerate(attractions[:10], 1):
            lines.append(f"{i}. {attr.get('name', 'Unknown')}")
            if attr.get("description"):
                lines.append(f"   {attr['description'][:100]}...")
        lines.append("")

    # Hotels
    hotels = results.get("hotels", {}).get("hotels", [])
    if hotels:
        lines.append("🏨 RECOMMENDED HOTELS")
        for i, hotel in enumerate(hotels[:5], 1):
            lines.append(f"{i}. {hotel.get('name', 'Unknown')}")
            lines.append(
                f"   Price: {hotel.get('price', 'N/A')} {hotel.get('currency', request.currency)}/night"
            )
            lines.append(
                f"   Rating: {hotel.get('review_score', 'N/A')}/10 ({hotel.get('review_count', 0)} reviews)"
            )
            lines.append(
                f"   Distance to attractions: {hotel.get('distance_to_attractions', 'N/A')}km"
            )
        lines.append("")

    # Itinerary
    itinerary = results.get("itinerary", {}).get("itinerary", {})
    if itinerary:
        lines.append("🗓️ DAILY ITINERARY")
        for day, activities in itinerary.items():
            lines.append(f"{day}:")
            if isinstance(activities, list):
                for activity in activities:
                    lines.append(f"  • {activity}")
            else:
                lines.append(f"  • {activities}")
        lines.append("")

    # Footer
    lines.append("Generated by AI Travel Planner")
    lines.append(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


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

    # Show agent status

    # Get user inputs from sidebar
    travel_request = create_sidebar_filters()

    # Main planning button
    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("🚀 Plan My Trip", type="primary", use_container_width=True):
            app = Graph()
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
            app.run(context, hotel_params, travel_request.attraction_focus)

            with st.spinner("🤖 AI agents are working on your travel plan..."):
                try:
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    status_text.text("🎯 Finding attractions...")
                    progress_bar.progress(25)

                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
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
                    display_hotels(results["hotels"], travel_request.currency)
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
