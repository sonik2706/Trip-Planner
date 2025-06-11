from typing import Dict, List
import streamlit as st
import pandas as pd
from frontend.models.travel_request import TravelRequest
import plotly.express as px

def is_hotel_in_budget(hotel: Dict, travel_request: TravelRequest) -> bool:
    """Check if hotel is within budget"""
    price = hotel.get("price", 0)

    if travel_request.min_price and price < travel_request.min_price:
        return False
    if travel_request.max_price and price > travel_request.max_price:
        return False

    return True


def get_budget_range_text(travel_request: TravelRequest) -> str:
    """Get budget range as text"""
    if travel_request.min_price and travel_request.max_price:
        return f"{travel_request.min_price}-{travel_request.max_price} {travel_request.currency}"
    elif travel_request.max_price:
        return f"Up to {travel_request.max_price} {travel_request.currency}"
    elif travel_request.min_price:
        return f"From {travel_request.min_price} {travel_request.currency}"
    else:
        return "Not specified"

def display_hotels(hotels_data: Dict, currency: str, travel_request: TravelRequest):
    """Display hotel recommendations with enhanced visualization"""
    st.subheader("🏨 Hotel Recommendations")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Hotels", hotels_data.get("total_found", 0))
    with col2:
        st.metric("In Budget", hotels_data.get("budget_hotels_count", 0))
    with col3:
        st.metric("Alternatives", hotels_data.get("alternative_hotels_count", 0))
    with col4:
        st.metric("Avg Price", hotels_data.get("avg_price", 0))

    # Show pro tips if available
    if hotels_data.get("pro_tips") and len(hotels_data["pro_tips"]) > 0:
        with st.expander("💡 Pro Tips from Hotel Expert"):
            for tip in hotels_data["pro_tips"]:
                st.write(f"• {tip}")

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(
        ["🏆 By Category", "📊 Price Analysis", "🗺️ Location Map"]
    )

    with tab1:
        # Display hotels by categories
        categories = hotels_data.get("categories", [])

        if categories:
            for i, category in enumerate(categories):
                category_name = category.get("name", "Recommended")
                category_hotels = category.get("hotels", [])

                if category_hotels:
                    # Category header with icon
                    category_icons = {
                        "Best Value": "💰",
                        "Best Location": "📍",
                        "Best Quality": "⭐"
                    }
                    icon = category_icons.get(category_name, "🏨")

                    st.markdown(f"### {icon} {category_name}")
                    st.markdown(f"*{len(category_hotels)} hotels in this category*")

                    # Display hotels in this category
                    for j, hotel in enumerate(category_hotels):
                        display_hotel_card(hotel, travel_request)

                    st.markdown("---")

    with tab2:
        # PROBLEM 1: Brak `all_hotels` w hotels_data - trzeba je utworzyć z categories
        all_hotels = []
        categories = hotels_data.get("categories", [])

        # Zbierz wszystkie hotele z kategorii
        for category in categories:
            category_name = category.get("name", "Unknown")
            for hotel in category.get("hotels", []):
                hotel_copy = hotel.copy()
                hotel_copy["category"] = category_name
                # PROBLEM 2: Dodaj value_score jeśli nie istnieje
                if "value_score" not in hotel_copy:
                    hotel_copy["value_score"] = hotel_copy.get("review_score", 7.0) / 10.0
                # PROBLEM 3: Dodaj distance_to_attractions jeśli nie istnieje
                if "distance_to_attractions" not in hotel_copy:
                    hotel_copy["distance_to_attractions"] = hotel_copy.get("average_distance_km", 1.0)
                all_hotels.append(hotel_copy)

        if all_hotels:
            df = pd.DataFrame(all_hotels)

            # PROBLEM 4: Sprawdź czy kolumny istnieją przed użyciem
            required_columns = ["price", "review_score", "value_score", "category", "name", "distance_to_attractions"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if not missing_columns:
                fig = px.scatter(
                    df,
                    x="price",
                    y="review_score",
                    size="value_score",
                    color="category",
                    hover_data=["name", "distance_to_attractions"],
                    title="Hotel Price vs Quality Analysis",
                    labels={
                        "price": f"Price ({df.iloc[0].get('currency', currency)})",
                        "review_score": "Review Score (0-10)",
                        "category": "Category"
                    }
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                # Price distribution by category
                st.subheader("💰 Price Distribution by Category")
                category_stats = []
                for category in categories:
                    cat_hotels = category.get("hotels", [])
                    if cat_hotels:
                        prices = [h["price"] for h in cat_hotels]
                        category_stats.append({
                            "Category": category.get("name", "Unknown"),
                            "Hotels": len(cat_hotels),
                            "Avg Price": f"{sum(prices) / len(prices):.0f}",
                            "Min Price": f"{min(prices):.0f}",
                            "Max Price": f"{max(prices):.0f}"
                        })

                if category_stats:
                    stats_df = pd.DataFrame(category_stats)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True)
            else:
                st.error(f"Missing required columns for analysis: {missing_columns}")
        else:
            st.warning("No hotel data available for price analysis")

    with tab3:
        # PROBLEM 5: Użyj prawdziwych współrzędnych zamiast mock data
        all_hotels = []
        for category in categories:
            for hotel in category.get("hotels", []):
                hotel_copy = hotel.copy()
                hotel_copy["category"] = category.get("name", "Unknown")
                all_hotels.append(hotel_copy)

        if all_hotels:
            map_data = []
            for i, hotel in enumerate(all_hotels):
                coord = hotel.get("coordinates", [{}])[0]
                lat = coord.get("lat")
                lon = coord.get("lon")

                if lat is not None and lon is not None:
                    map_data.append({
                        "name": hotel["name"],
                        "lat": lat,
                        "lon": lon,
                        "price": hotel["price"],
                        "category": hotel["category"],
                        "review_score": hotel.get("review_score", 7.0)
                    })

            if map_data:
                map_df = pd.DataFrame(map_data)

                # PROBLEM 7: Sprawdź czy plotly może utworzyć mapę
                try:
                    fig = px.scatter_mapbox(
                        map_df,
                        lat="lat",
                        lon="lon",
                        hover_name="name",
                        hover_data=["price", "category", "review_score"],
                        color="category",
                        size="review_score",
                        zoom=13,
                        height=500,
                        title="Hotel Locations by Category",
                        mapbox_style="open-street-map"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Dodaj prostą mapę Streamlit jako backup
                    st.subheader("📍 Simple Hotel Locations")
                    st.map(map_df[["lat", "lon"]], zoom=12)

                except Exception as e:
                    st.error(f"Error creating interactive map: {e}")
                    # Fallback do prostej mapy
                    st.subheader("📍 Hotel Locations")
                    st.map(map_df[["lat", "lon"]], zoom=12)

                # Hotel details table
                st.subheader("🏨 Hotel Details")
                display_df = map_df[["name", "price", "category", "review_score"]].copy()
                display_df.columns = ["Hotel Name", "Price", "Category", "Review Score"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No hotel location data available")
        else:
            st.warning("No hotel data available for mapping")


def display_hotel_card(hotel: Dict, travel_request: TravelRequest):
    """Display individual hotel card"""
    with st.container():
        # Hotel header with budget indicator
        col_header1, col_header2 = st.columns([4, 1])

        with col_header1:
            st.markdown(f"**🏨 {hotel.get('name', 'Unknown Hotel')}**")

        with col_header2:
            # Budget indicator
            if is_hotel_in_budget(hotel, travel_request):
                st.success("✅ In Budget")
            else:
                st.warning("💰 Over Budget")

        # Main hotel info
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.write(f"📍 {hotel.get('location', 'Location not specified')}")
            st.caption(f"⭐ {hotel.get('review_score', 0)}/10 ({hotel.get('review_count', 0)} reviews)")

            # Show why recommended - this is key info from hotel agent
            if hotel.get('why_recommended'):
                st.info(f"💡 **Why recommended:** {hotel['why_recommended']}")

        with col2:
            price = hotel.get('price', 0)
            currency = hotel.get('currency', 'EUR')
            st.metric("Price/night", f"{price} {currency}")
            distance = hotel.get('average_distance_km')
            if distance is None:
                distance = 0
            st.write(f"🏃 {distance:.1f}km to attractions")


        with col3:
            stars = hotel.get('stars', 0)
            st.write(f"{'⭐' * stars}")
            if hotel.get('link'):
                st.markdown(f"[Book Now]({hotel['link']})")

        # Progress bars for scores
        value_score = hotel.get('value_score', 0.5)
        st.progress(value_score, text=f"Value Score: {value_score:.2f}")

        st.markdown("---")
