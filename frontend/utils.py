from typing import Dict
import streamlit as st

from frontend.models.travel_request import TravelRequest

def load_css(file):
    """Load CSS from a specified file and apply it to the Streamlit app.

    Args:
        file (str): The path to the CSS file.
    """
    with open(file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)