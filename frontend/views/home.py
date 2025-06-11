import streamlit as st


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