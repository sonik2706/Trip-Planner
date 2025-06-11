import streamlit as st
import json
from datetime import datetime
from typing import Dict
from frontend.models.travel_request import TravelRequest

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