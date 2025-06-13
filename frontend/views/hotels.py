from typing import Dict, List
import streamlit as st
import pandas as pd
from frontend.models.travel_request import TravelRequest
import plotly.express as px

def is_hotel_in_budget(hotel: Dict, travel_request: TravelRequest) -> bool:
    """Check if hotel is within budget"""
    price = hotel.get("price", 0)

    if price is None:
        return False

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

def display_hotels(hotels_data, currency: str, travel_request: TravelRequest):
    """Display hotel recommendations with enhanced visualization"""
    st.subheader("🏨 Hotel Recommendations")
    
    # Debug: Show what data we're receiving
    with st.expander("🔍 Debug: Hotel Data Structure"):
        st.write("**Type:**", type(hotels_data))
        st.write("**Keys:**", list(hotels_data.keys()) if isinstance(hotels_data, dict) else "Not a dict")
        st.json(hotels_data)

    # Handle different data structures
    all_hotels = []
    categories = []
    
    if isinstance(hotels_data, list):
        # If hotels_data is a list of hotels directly
        all_hotels = hotels_data
        categories = [{"name": "Selected Hotels", "hotels": hotels_data}]
    elif isinstance(hotels_data, dict):
        # First check if we have all_hotels key (your current case)
        if "all_hotels" in hotels_data and hotels_data["all_hotels"]:
            all_hotels = hotels_data["all_hotels"]
            # Group hotels by category if they have category info
            categories_dict = {}
            for hotel in all_hotels:
                category = hotel.get("category", "Hotels")
                if category not in categories_dict:
                    categories_dict[category] = []
                categories_dict[category].append(hotel)
            
            # Convert to categories format
            categories = [{"name": cat_name, "hotels": cat_hotels} 
                         for cat_name, cat_hotels in categories_dict.items()]
            
        elif "categories" in hotels_data and hotels_data["categories"]:
            # Expected structure with categories
            categories = hotels_data.get("categories", [])
            for category in categories:
                all_hotels.extend(category.get("hotels", []))
        elif "hotels" in hotels_data:
            # Alternative structure with hotels key
            all_hotels = hotels_data.get("hotels", [])
            categories = [{"name": "Hotels", "hotels": all_hotels}]
        else:
            # Try to find hotel-like objects in the dict
            for key, value in hotels_data.items():
                if isinstance(value, list) and value:
                    # Check if it looks like a list of hotels
                    first_item = value[0]
                    if isinstance(first_item, dict) and 'name' in first_item:
                        all_hotels = value
                        categories = [{"name": key.title(), "hotels": value}]
                        break
    
    if not all_hotels:
        st.error("No hotel data found. Please check the data structure.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Hotels", len(all_hotels))
    with col2:
        budget_count = sum(1 for hotel in all_hotels if is_hotel_in_budget(hotel, travel_request))
        st.metric("In Budget", budget_count)
    with col3:
        st.metric("Categories", len(categories))
    with col4:
        prices = [h.get("price", 0) for h in all_hotels if h.get("price")]
        avg_price = sum(prices) / len(prices) if prices else 0
        st.metric("Avg Price", f"{avg_price:.0f} {currency}")

    # Show pro tips if available
    if isinstance(hotels_data, dict) and hotels_data.get("pro_tips"):
        with st.expander("💡 Pro Tips from Hotel Expert"):
            for tip in hotels_data["pro_tips"]:
                st.write(f"• {tip}")

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(
        ["🏆 Hotels List", "📊 Price Analysis", "🗺️ Location Map"]
    )

    with tab1:
        # Display hotels by categories or as simple list
        if categories:
            for i, category in enumerate(categories):
                category_name = category.get("name", "Hotels")
                category_hotels = category.get("hotels", [])

                if category_hotels:
                    # Category header with icon
                    category_icons = {
                        "Best Value": "💰",
                        "Best Location": "📍",
                        "Best Quality": "⭐",
                        "Selected Hotels": "🏨"
                    }
                    icon = category_icons.get(category_name, "🏨")

                    st.markdown(f"### {icon} {category_name}")
                    st.markdown(f"*{len(category_hotels)} hotels in this category*")

                    # Display hotels in this category
                    for j, hotel in enumerate(category_hotels):
                        try:
                            display_hotel_card(hotel, travel_request)
                        except Exception as e:
                            st.error(f"Error displaying hotel {j+1}: {e}")
                            # Show basic info as fallback
                            st.write(f"**Hotel**: {hotel.get('name', 'Unknown')}")
                            if 'price' in hotel:
                                st.write(f"**Price**: {hotel['price']} {hotel.get('currency', currency)}")

                    if i < len(categories) - 1:  # Don't add separator after last category
                        st.markdown("---")
        else:
            # Fallback: display all hotels without categories
            st.markdown("### 🏨 Available Hotels")
            for i, hotel in enumerate(all_hotels):
                try:
                    display_hotel_card(hotel, travel_request)
                except Exception as e:
                    st.error(f"Error displaying hotel {i+1}: {e}")

    with tab2:
        # Price analysis
        if all_hotels:
            # Prepare data for analysis
            analysis_hotels = []
            for hotel in all_hotels:
                hotel_copy = hotel.copy()
                
                # Add missing fields with defaults
                if "value_score" not in hotel_copy:
                    review_score = hotel_copy.get("review_score", 7.0)
                    hotel_copy["value_score"] = review_score / 10.0 if review_score else 0.7
                
                if "distance_to_attractions" not in hotel_copy:
                    hotel_copy["distance_to_attractions"] = hotel_copy.get("average_distance_km", 1.0)
                
                if "category" not in hotel_copy:
                    hotel_copy["category"] = "Hotels"
                
                analysis_hotels.append(hotel_copy)

            try:
                df = pd.DataFrame(analysis_hotels)
                
                # Check required columns
                required_columns = ["price", "review_score", "name"]
                available_columns = [col for col in required_columns if col in df.columns]
                
                if len(available_columns) >= 2:
                    # Create scatter plot
                    fig = px.scatter(
                        df,
                        x="price" if "price" in df.columns else df.columns[0],
                        y="review_score" if "review_score" in df.columns else df.columns[1],
                        size="value_score" if "value_score" in df.columns else None,
                        color="category" if "category" in df.columns else None,
                        hover_data=["name"] + ([col for col in ["distance_to_attractions", "stars"] if col in df.columns]),
                        title="Hotel Analysis",
                        labels={
                            "price": f"Price ({currency})",
                            "review_score": "Review Score"
                        }
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Simple price statistics
                st.subheader("💰 Price Statistics")
                prices = [h.get("price", 0) for h in all_hotels if h.get("price")]
                if prices:
                    stats_data = {
                        "Metric": ["Average", "Minimum", "Maximum", "Hotels Count"],
                        "Value": [
                            f"{sum(prices)/len(prices):.0f} {currency}",
                            f"{min(prices):.0f} {currency}",
                            f"{max(prices):.0f} {currency}",
                            str(len(prices))
                        ]
                    }
                    st.dataframe(pd.DataFrame(stats_data), hide_index=True)
                
            except Exception as e:
                st.error(f"Error creating price analysis: {e}")
                # Fallback: simple text statistics
                prices = [h.get("price", 0) for h in all_hotels if h.get("price")]
                if prices:
                    st.write(f"**Price Range:** {min(prices)} - {max(prices)} {currency}")
                    st.write(f"**Average Price:** {sum(prices)/len(prices):.0f} {currency}")
        else:
            st.warning("No hotel data available for analysis")

    with tab3:
        # Location map
        if all_hotels:
            try:
                map_data = []
                for hotel in all_hotels:
                    # Try different coordinate formats
                    lat, lon = None, None
                    
                    # Check different possible coordinate structures
                    if "coordinates" in hotel:
                        coords = hotel["coordinates"]
                        if isinstance(coords, list) and coords:
                            coord = coords[0]
                            lat = coord.get("lat")
                            lon = coord.get("lon")
                        elif isinstance(coords, dict):
                            lat = coords.get("lat")
                            lon = coords.get("lon")
                    
                    # Alternative coordinate keys
                    if lat is None:
                        lat = hotel.get("latitude") or hotel.get("lat")
                    if lon is None:
                        lon = hotel.get("longitude") or hotel.get("lon") or hotel.get("lng")

                    if lat is not None and lon is not None:
                        map_data.append({
                            "name": hotel.get("name", "Hotel"),
                            "lat": float(lat),
                            "lon": float(lon),
                            "price": hotel.get("price", 0),
                            "review_score": hotel.get("review_score", 0)
                        })

                if map_data:
                    map_df = pd.DataFrame(map_data)
                    
                    # Try interactive map first
                    try:
                        fig = px.scatter_mapbox(
                            map_df,
                            lat="lat",
                            lon="lon",
                            hover_name="name",
                            hover_data=["price", "review_score"],
                            zoom=13,
                            height=500,
                            title="Hotel Locations",
                            mapbox_style="open-street-map"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        # Fallback to simple map
                        st.subheader("📍 Hotel Locations")
                        st.map(map_df[["lat", "lon"]], zoom=12)

                    # Hotel details table
                    st.subheader("🏨 Hotel Summary")
                    display_df = map_df[["name", "price", "review_score"]].copy()
                    display_df.columns = ["Hotel Name", f"Price ({currency})", "Review Score"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No hotel location data available for mapping")
            except Exception as e:
                st.error(f"Error creating map: {e}")
        else:
            st.warning("No hotel data available for mapping")


def display_hotel_card(hotel: Dict, travel_request: TravelRequest):
    """Display individual hotel card with better error handling"""
    try:
        with st.container():
            # Hotel header with budget indicator
            col_header1, col_header2 = st.columns([4, 1])

            with col_header1:
                hotel_name = hotel.get('name', 'Unknown Hotel')
                st.markdown(f"**🏨 {hotel_name}**")

            with col_header2:
                # Budget indicator
                try:
                    if is_hotel_in_budget(hotel, travel_request):
                        st.success("✅ In Budget")
                    else:
                        st.warning("💰 Over Budget")
                except:
                    st.info("💰 Budget N/A")

            # Main hotel info
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                location = hotel.get('location', 'Location not specified')
                st.write(f"📍 {location}")
                
                review_score = hotel.get('review_score', 0)
                review_count = hotel.get('review_count', 0)
                st.caption(f"⭐ {review_score}/10 ({review_count} reviews)")

                # Show why recommended
                if hotel.get('why_recommended'):
                    st.info(f"💡 **Why recommended:** {hotel['why_recommended']}")

            with col2:
                price = hotel.get('price', 0)
                currency = hotel.get('currency', 'EUR')
                st.metric("Price", f"{price} {currency}")
                
                distance = hotel.get('average_distance_km', hotel.get('distance_to_attractions', 0))
                if distance is None:
                    distance = 0
                st.write(f"🏃 {distance:.1f}km to attractions")

            with col3:
                stars = hotel.get('stars', 0)
                if stars is None:
                    stars = 0
                if stars > 0:
                    st.write(f"{'⭐' * int(stars)}")
                
                if hotel.get('link'):
                    st.markdown(f"[Book Now]({hotel['link']})")

            # Progress bars for scores
            value_score = hotel.get('value_score', 0.5)
            if value_score is not None:
                st.progress(float(value_score), text=f"Value Score: {value_score:.2f}")

            st.markdown("---")
            
    except Exception as e:
        st.error(f"Error displaying hotel card: {e}")
        # Minimal fallback display
        st.write(f"**🏨 {hotel.get('name', 'Hotel')}**")
        if 'price' in hotel:
            st.write(f"💰 {hotel['price']} {hotel.get('currency', 'EUR')}")
        st.markdown("---")