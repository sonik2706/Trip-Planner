import streamlit as st
from typing import Dict
from frontend.models.travel_request import TravelRequest

def display_itinerary(itinerary_dict: Dict):
    for day in itinerary_dict["days"]:
        with st.container():
            st.markdown(f"### 📅 Day {day['day']}")
            st.write("**Planned Attractions:**")
            if day["attractions"]:
                for attraction in day["attractions"]:
                    st.markdown(f"- {attraction['name']}")
                st.markdown(f"[🗺️ Google Maps Route]({day['map_link']})")
                st.divider()

    # Omitted attractions
    if itinerary_dict.get("omitted_attractions"):
        st.markdown("### ⚠️ Omitted Attractions")
        st.info("These were skipped due to time or distance constraints:")
        for attr in itinerary_dict["omitted_attractions"]:
            st.markdown(f"- {attr['name']}")
            
    with st.expander("📦 Show Raw JSON"):
        st.json(itinerary_dict)