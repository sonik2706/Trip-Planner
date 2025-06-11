import streamlit as st
import pandas as pd
from typing import Dict
from frontend.models.travel_request import TravelRequest


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