"""

"""
import graphviz

from langgraph.graph import StateGraph, END
from typing import TypedDict

from Utils.LocationGeocoder import LocationGeocoder
from agents.prompt_agent import PromptAgent
from agents.attraction_agent import AttractionAgent
from agents.hotel_agent import HotelAgent
from agents.map_agent import MapAgent

from settings.config import Config


class State(TypedDict, total=False):
    country: str
    city: str
    context: str
    focus: str
    trip_preferences: dict
    attractions: list
    hotels: list
    itinerary: dict
    hotel_params: dict
    num_attractions: int


class Graph:
    def __init__(self):
        self.config = Config()
        self.prompt_agent = PromptAgent(self.config)
        self.hotel_agent = HotelAgent(self.config)
        self.attraction_agent = AttractionAgent(self.config)
        self.map_agent = MapAgent(self.config)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(State)

        # Define nodes
        graph.add_node("verify_prompt", self._verify_prompt)
        graph.add_node("search_for_attractions", self._generate_attractions)
        graph.add_node("find_hotels", self._generate_hotels)
        # graph.add_node("plan_the_trip", self._build_itinerary)
        # graph.add_node("generate_response", self._generate_response)

        # Set entry and conditional routing
        graph.set_entry_point("verify_prompt")
        graph.add_edge("verify_prompt", "search_for_attractions")
        graph.add_edge("search_for_attractions", "find_hotels")
        # Final steps
        # graph.add_edge("find_hotels", "plan_the_trip")
        # graph.add_edge("plan_the_trip", "generate_response")
        # graph.add_edge("search_for_attractions", END)

        self._raw_graph = graph

        return graph.compile()

    def run(self, context: str, hotel_params: dict, focus: str, num_attractions: int) -> dict:
        initial_state = {
            "country": hotel_params["country"],
            "city": hotel_params["city"],
            "context": context,
            "num_attractions": num_attractions,
            "hotel_params": hotel_params,
            "focus": focus
        }

        print("Initial state:", initial_state)

        try:
            final_state = self.graph.invoke(initial_state)
            print(final_state)
            return final_state
        except Exception as e:
            print(f"Graph execution error: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "request": initial_state
            }

    # === Node Functions ===
    def _verify_prompt(self, state: State) -> State:
        print("Verifying prompt...")
        if state.get("context", "").strip():
            print("SKIPPING PROMT VERIFICATION!!!")
            return state

        preferences = self.prompt_agent.extract(state["country"], state["city"], state["context"])
        state["trip_preferences"] = preferences
        return state

    def _generate_attractions(self, state: State) -> State:
        print("Generating attractions...")
        city = state["city"]
        focus = state["focus"]
        num_attractions = state["num_attractions"]
        attractions = self.attraction_agent.find_attractions(
            city_name=city, num_attractions=num_attractions, focus=focus
        )
        state["attractions"] = attractions
        return state

    def _generate_hotels(self, state: State) -> State:
        print("Finding hotels...")
        hotel_params = state["hotel_params"]
        attractions = state["attractions"]
        geocoder = LocationGeocoder()
        hotels = self.hotel_agent.get_hotel_recommendations(
            city=hotel_params["city"],
            attractions=geocoder.get_attraction_coordinates(attractions),
            budget_range=(hotel_params["min_price"], hotel_params["max_price"]),
            min_review_score=hotel_params["min_review_score"],
            checkin_date=hotel_params["checkin_date"],
            checkout_date=hotel_params["checkout_date"],
            use_agent=True,
            currency=hotel_params["currency"],)
        state["hotels"] = hotels
        return state

    def _build_itinerary(self, state: State) -> State:
        print("Generating itinery...")
        
        accomodation = "city center"
        days = 3
        attractions = [a["name"] for a in state["attractions"]]
        itinerary = self.map_agent.optimize(
            city=city,
            days=days,
            accomodation_address=accomodation,
            list_attractions=attractions,
        )
        state["itinerary"] = itinerary
        return state

    def _generate_response(self):
        pass

    def visualize_graph(self, filename="manager_graph.jpg"):
        img_bytes = self.graph.get_graph().draw_mermaid_png()
        with open("graph.png", "wb") as f:
            f.write(img_bytes)
