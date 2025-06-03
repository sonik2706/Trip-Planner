import json
import requests
from typing import Dict, List, Optional, Literal
from datetime import date, datetime
from urllib.parse import quote_plus

import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from agents.utils.json_formatter import GenericLLMFormatter


class HotelAgent:
    def __init__(self, config):
        self.config = config
        self._load_prompts("prompts/booking_agent_prompt.yaml")
        self._setup_llm()
        self._setup_tools()
        self._setup_agent()

    def _load_prompts(self, file_path: str):

        with open(file_path, "r", encoding="utf-8") as file:
            self.prompts = yaml.safe_load(file)

    def _setup_llm(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    def _setup_tools(self):
        self.tools = [
            Tool(
                name="search_and_rank_hotels",
                func=self._search_and_rank_hotels,
                description=(
                    "Search for hotels and automatically rank them by distance to attractions, reviews, price and stars. "
                    "Input should be JSON with city, dates, adults, rooms, currency, attractions, and filtering criteria."
                )
            )
        ]

    def _setup_agent(self):
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )

    def _get_destination_id(self, city: str, country: str = "") -> tuple:
        """Get destination ID and type for a location - simplified and more reliable"""
        try:
            headers = {
                "X-RapidAPI-Key": self.config.BOOKING_API_KEY,
                "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
            }

            dest_url = "https://booking-com.p.rapidapi.com/v1/hotels/locations"
            params = {"name": city, "locale": "en-gb"}

            if country:
                params["country"] = country

            response = requests.get(dest_url, headers=headers, params=params)
            print(f"🔍 Location API response status: {response.status_code}")

            if response.status_code != 200:
                raise Exception(f"Location API failed: {response.status_code}")

            data = response.json()
            if not data or len(data) == 0:
                raise Exception(f"No location found for: {city}")

            dest_id = data[0].get("dest_id")
            dest_type = data[0].get("dest_type", "city")

            if not dest_id:
                raise Exception(f"No destination ID found for: {city}")

            print(f"✅ Found destination: {dest_id} (type: {dest_type}) for {city}")
            return str(dest_id), dest_type

        except Exception as e:
            print(f"❌ Error getting destination ID: {str(e)}")
            raise

    def _search_and_rank_hotels(self, params_str: str) -> str:
        """Jedna funkcja do wyszukiwania i rankingu hoteli z inteligentnym fallback"""
        try:
            params_str = (
                params_str.replace("```json", "")  # usuwa nagłówek z nazwą języka
                .replace("```", "")  # usuwa zamykające (i ewentualne inne) back-ticki
            )

            params = json.loads(params_str)
            print(f"✅ Sparsowano params dla: {params.get('city')}")
            print(f"🎯 Otrzymane atrakcje: {len(params.get('attractions', []))}")

            # Debug - pokaż atrakcje
            attractions = params.get("attractions", [])
            if attractions:
                for i, attr in enumerate(attractions[:2]):
                    print(f"  📍 Atrakcja {i + 1}: {attr.get('name', 'N/A')} -> {attr.get('coords', 'N/A')}")
            else:
                print("  ❌ BRAK ATRAKCJI - sprawdź dlaczego!")

            # 1. Pobierz destination ID
            city = params.get("city", "")
            country = params.get("country", "")
            dest_id, dest_type = self._get_destination_id(city, country)

            # 2. Wyszukaj hotele
            headers = {
                "X-RapidAPI-Key": self.config.BOOKING_API_KEY,
                "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
            }

            search_query = {
                "dest_id": dest_id,
                "dest_type": dest_type,
                "checkin_date": params.get("checkin_date"),
                "checkout_date": params.get("checkout_date"),
                "adults_number": params.get("adults_number", 2),
                "room_number": params.get("room_number", 1),
                "locale": "en-gb",
                "currency": params.get("currency", "USD"),
                "order_by": "popularity",
                "page_number": "0",
                "units": "metric",
                "filter_by_currency": params.get("currency", "USD"),
            }

            # Pierwsza próba z filtrami cenowymi
            original_min_price = params.get("min_price")
            original_max_price = params.get("max_price")

            if original_min_price:
                search_query["price_min"] = original_min_price
            if original_max_price:
                search_query["price_max"] = original_max_price

            response = requests.get(
                "https://booking-com.p.rapidapi.com/v1/hotels/search",
                headers=headers,
                params=search_query
            )

            if response.status_code != 200:
                return json.dumps({"hotels": [], "status": "error", "message": f"API failed: {response.status_code}"})

            # 3. Przetwórz wyniki
            data = response.json()
            hotels_raw = data.get("result", [])
            print(f"🏨 Znaleziono {len(hotels_raw)} hoteli w oryginalnym przedziale cenowym")

            # Jeśli za mało wyników, rozszerz wyszukiwanie
            if len(hotels_raw) < 5:
                print("🔍 Za mało wyników, rozszerzam wyszukiwanie...")
                # Usuń filtry cenowe i szukaj ponownie
                search_query_expanded = search_query.copy()
                search_query_expanded.pop("price_min", None)
                search_query_expanded.pop("price_max", None)

                response = requests.get(
                    "https://booking-com.p.rapidapi.com/v1/hotels/search",
                    headers=headers,
                    params=search_query_expanded
                )

                if response.status_code == 200:
                    expanded_data = response.json()
                    hotels_raw = expanded_data.get("result", [])
                    print(f"🏨 Po rozszerzeniu: {len(hotels_raw)} hoteli")

            hotels = []
            attractions = params.get("attractions", [])

            for hotel in hotels_raw:
                price = hotel.get("min_total_price")
                if not price:
                    continue

                review_score = float(hotel.get("review_score", 0) or 0)
                lat, lon = hotel.get("latitude"), hotel.get("longitude")
                coords = [lat, lon] if lat and lon else None

                # Star rating z fallback
                star_class = hotel.get("class") or 0

                # Oblicz odległość do atrakcji
                distance_to_attractions = self._calculate_distance_score_detailed(coords, attractions)

                # Debug - sprawdź czy odległość się oblicza
                if distance_to_attractions != float('inf'):
                    print(f"  ✅ Hotel {hotel.get('hotel_name', 'Unknown')}: {distance_to_attractions}km od atrakcji")
                else:
                    print(f"  ⚠️ Hotel {hotel.get('hotel_name', 'Unknown')}: brak odległości (inf)")

                # Sprawdź czy hotel jest w oryginalnym budżecie
                in_budget = True
                budget_note = ""
                if original_min_price and price < original_min_price:
                    in_budget = False
                    budget_note = f"Poniżej budżetu (min: {original_min_price})"
                elif original_max_price and price > original_max_price:
                    in_budget = False
                    budget_note = f"Powyżej budżetu (max: {original_max_price})"

                hotel_data = {
                    "name": hotel.get("hotel_name", "Unknown"),
                    "price": float(price),
                    "review_score": review_score,
                    "review_count": hotel.get("review_nr", 0),
                    "location": hotel.get("address", ""),
                    "link": hotel.get("url", ""),
                    "coords": coords,
                    "hotel_id": hotel.get("hotel_id"),
                    "star_class": int(star_class),
                    "currency": hotel.get("currency_code", params.get("currency", "USD")),
                    "distance_to_attractions": distance_to_attractions,
                    "distance_from_center": float(hotel.get("distance", 0)),
                    "in_original_budget": in_budget,
                    "budget_note": budget_note,
                    "value_score": 0  # Obliczone niżej
                }

                # Oblicz value score
                hotel_data["value_score"] = self._calculate_value_score(hotel_data)

                hotels.append(hotel_data)

            # 4. Filtruj i rankinguj
            min_review_score = params.get("min_review_score", 0)
            star_classes = params.get("star_classes", [])
            max_hotels = params.get("max_hotels", 10)

            print(f"🔧 Rozpoczynam filtrowanie {len(hotels)} hoteli")
            print(f"🎯 Atrakcje do sprawdzenia: {len(attractions)}")

            # Sprawdź czy atrakcje mają właściwy format
            for i, attr in enumerate(attractions):
                if attr.get("coords"):
                    print(f"  Atrakcja {i + 1}: {attr.get('name', 'N/A')} -> {attr['coords']}")
                else:
                    print(f"  ⚠️ Atrakcja {i + 1} nie ma współrzędnych!")

            # Rozdziel hotele na te w budżecie i poza budżetem
            budget_hotels = [h for h in hotels if h["in_original_budget"]]
            alternative_hotels = [h for h in hotels if not h["in_original_budget"]]

            print(f"💰 Hotele w budżecie: {len(budget_hotels)}")
            print(f"🔄 Hotele alternatywne: {len(alternative_hotels)}")

            # Filtruj oba zestawy
            def apply_filters(hotel_list, list_name):
                print(f"\n🔍 Filtruję {list_name}: {len(hotel_list)} hoteli")
                filtered = []
                for i, hotel in enumerate(hotel_list):
                    # Sprawdź podstawowe filtry
                    if min_review_score and hotel["review_score"] < min_review_score:
                        print(f"  ❌ Hotel {i + 1}: ocena za niska ({hotel['review_score']} < {min_review_score})")
                        continue
                    if star_classes and hotel["star_class"] not in star_classes:
                        print(
                            f"  ❌ Hotel {i + 1}: zła kategoria gwiazdkowa ({hotel['star_class']} nie w {star_classes})")
                        continue

                    # Oblicz odległość jeśli są atrakcje
                    if attractions:
                        distance = self._calculate_distance_score_detailed(hotel.get("coords"), attractions)
                        hotel["distance_to_attractions"] = distance
                    else:
                        hotel["distance_to_attractions"] = float('inf')
                        print(f"  ⚠️ Hotel {i + 1}: brak atrakcji do sprawdzenia")

                    # Ranking score
                    distance_score = 1 / (hotel["distance_to_attractions"] + 0.1) if hotel[
                                                                                         "distance_to_attractions"] != float(
                        'inf') else 0
                    review_score = hotel["review_score"] / 10.0
                    value_score = hotel["value_score"]
                    star_score = hotel["star_class"] / 5.0

                    hotel["ranking_score"] = (
                            distance_score * 0.35 +
                            review_score * 0.30 +
                            value_score * 0.25 +
                            star_score * 0.10
                    )

                    print(
                        f"  ✅ Hotel {i + 1}: {hotel['name'][:30]}... - odległość: {hotel['distance_to_attractions']}km, ranking: {hotel['ranking_score']:.3f}")
                    filtered.append(hotel)

                print(f"  📊 Wynik filtrowania {list_name}: {len(filtered)}/{len(hotel_list)} hoteli")
                return filtered

            budget_filtered = apply_filters(budget_hotels, "budżetowe")
            alternative_filtered = apply_filters(alternative_hotels, "alternatywne")

            # 5. Sortuj i kombinuj wyniki
            budget_filtered.sort(key=lambda x: x["ranking_score"], reverse=True)
            alternative_filtered.sort(key=lambda x: x["ranking_score"], reverse=True)

            # Preferuj hotele w budżecie, ale zawsze dołącz alternatywy
            final_hotels = []

            # Najpierw hotele w budżecie
            budget_count = min(len(budget_filtered), max_hotels)
            final_hotels.extend(budget_filtered[:budget_count])

            # Potem alternatywy jeśli jest miejsce
            remaining_slots = max_hotels - len(final_hotels)
            if remaining_slots > 0:
                final_hotels.extend(alternative_filtered[:remaining_slots])

            # Dodaj pozycję rankingu i kategorie
            budget_hotels_count = sum(1 for h in final_hotels if h["in_original_budget"])
            alternative_hotels_count = len(final_hotels) - budget_hotels_count

            for i, hotel in enumerate(final_hotels):
                hotel["ranking_position"] = i + 1
                hotel["category"] = "W budżecie" if hotel["in_original_budget"] else "Alternatywa"

            return json.dumps({
                "hotels": final_hotels,
                "total_found": len(final_hotels),
                "budget_hotels_count": budget_hotels_count,
                "alternative_hotels_count": alternative_hotels_count,
                "original_budget": f"{original_min_price or 'brak'} - {original_max_price or 'brak'} {params.get('currency', 'USD')}",
                "search_expanded": len(hotels_raw) > len(budget_hotels),
                "status": "success"
            })

        except Exception as e:
            print(f"❌ Błąd wyszukiwania: {str(e)}")
            return json.dumps({"hotels": [], "status": "error", "message": str(e)})

    def _calculate_distance_score_detailed(self, hotel_coords, attractions):
        """Oblicz szczegółową odległość do atrakcji - NAPRAWIONA WERSJA"""
        # print(f"🔍 Sprawdzam odległość dla hotelu: {hotel_coords}")
        # print(f"🎯 Liczba atrakcji: {len(attractions) if attractions else 0}")

        if not hotel_coords or not attractions:
            # print("❌ Brak współrzędnych hotelu lub atrakcji")
            return float('inf')

        try:
            distances = []
            for i, attraction in enumerate(attractions):
                attr_coords = attraction.get("coords")
                if attr_coords and len(attr_coords) >= 2:
                    # Euclidean distance converted to approximate km
                    lat_diff = hotel_coords[0] - attr_coords[0]
                    lon_diff = hotel_coords[1] - attr_coords[1]
                    distance = ((lat_diff ** 2) + (lon_diff ** 2)) ** 0.5 * 111
                    distances.append(distance)
                    # print(f"  📍 {attraction.get('name', f'Atrakcja {i + 1}')}: {distance:.2f}km")
                # else:
                    # print(f"  ❌ Atrakcja {i + 1} nie ma poprawnych współrzędnych")

            if distances:
                avg_distance = sum(distances) / len(distances)
                result = round(avg_distance, 2)
                # print(f"  ✅ Średnia odległość: {result}km")
                return result
            # else:
            #     print("  ❌ Żadna atrakcja nie ma poprawnych współrzędnych")
            #     return float('inf')

        except Exception as e:
            # print(f"  ❌ Błąd obliczania odległości: {e}")
            return float('inf')

    def _calculate_distance_score(self, hotel: Dict, attractions: List[Dict]) -> float:
        """Calculate average distance from hotel to attractions"""
        if not hotel.get("coords") or not attractions:
            return float('inf')

        try:
            hotel_coords = hotel["coords"]
            distances = []

            for attraction in attractions:
                attr_coords = attraction.get("coords")
                if attr_coords and len(attr_coords) >= 2:
                    lat_diff = hotel_coords[0] - attr_coords[0]
                    lon_diff = hotel_coords[1] - attr_coords[1]
                    distance = ((lat_diff ** 2) + (lon_diff ** 2)) ** 0.5 * 111
                    distances.append(distance)

            return sum(distances) / len(distances) if distances else float('inf')

        except Exception as e:
            print(f"⚠️ Error calculating distance: {e}")
            return float('inf')

    def _calculate_value_score(self, hotel: Dict) -> float:
        """Calculate comprehensive value score"""
        try:
            price = hotel.get("price", 0)
            review_score = hotel.get("review_score", 0)
            star_class = hotel.get("star_class", 0)
            review_count = hotel.get("review_count", 0)

            if price <= 0:
                return 0

            # Normalize components (0-1 scale)
            review_component = review_score / 10.0  # 0-10 scale
            star_component = star_class / 5.0  # 0-5 scale
            price_component = min(1000 / price, 1.0)  # Inverse price (cheaper = better)

            # Review count bonus (more reviews = more reliable)
            review_count_bonus = min(review_count / 1000, 0.2)  # Max 0.2 bonus

            # Weighted score
            value_score = (
                    review_component * 0.4 +  # 40% review quality
                    star_component * 0.2 +  # 20% star rating
                    price_component * 0.3 +  # 30% price value
                    review_count_bonus * 0.1  # 10% review reliability
            )

            return round(value_score, 4)

        except Exception as e:
            print(f"⚠️ Error calculating value score: {e}")
            return 0

    def search_hotels(
            self,
            city: str,
            country: str = "",
            checkin_date: str = "",
            checkout_date: str = "",
            adults_number: int = 2,
            room_number: int = 1,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            currency: str = "USD",
            star_classes: Optional[List[int]] = None,
            min_review_score: float = 0.0,
            max_hotels: int = 10,
            attractions: Optional[List[Dict]] = None,
            use_agent: bool = True
    ) -> Dict:
        """Uproszczone wyszukiwanie hoteli - jedna funkcja do wszystkiego"""

        search_params = {
            "city": city,
            "country": country,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "adults_number": adults_number,
            "room_number": room_number,
            "currency": currency,
            "min_price": min_price,
            "max_price": max_price,
            "star_classes": star_classes,
            "min_review_score": min_review_score,
            "max_hotels": max_hotels,
            "attractions": attractions or []
        }

        if use_agent:
            try:
                # Przygotuj atrakcje jako JSON string
                attractions_json = json.dumps(attractions or [])

                template_params = {
                    "city": city,
                    "country": country or "",
                    "checkin_date": checkin_date,
                    "checkout_date": checkout_date,
                    "adults_number": adults_number,
                    "room_number": room_number,
                    "currency": currency,
                    "min_price": min_price or "null",
                    "max_price": max_price or "null",
                    "star_classes": json.dumps(star_classes or []),
                    "min_review_score": min_review_score,
                    "max_hotels": max_hotels,
                    "attractions": attractions_json  # JSON string gotowy do wstawienia
                }

                prompt = self.prompts.get('search_template', '').format(**template_params)
                print(f"🤖 Używam AI agenta z {len(attractions or [])} atrakcjami...")
                print(f"🔍 Atrakcje przekazane: {attractions_json}")

                response = self.agent.invoke(prompt)

                if isinstance(response, dict):
                    return response
                elif isinstance(response, str):
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        pass

            except Exception as e:
                print(f"⚠️ Agent failed: {str(e)}, używam bezpośredniego wyszukiwania")

        # Bezpośrednie wyszukiwanie (fallback lub gdy use_agent=False)
        print(f"🔧 Bezpośrednie wyszukiwanie...")
        result = self._search_and_rank_hotels(json.dumps(search_params))
        return json.loads(result)

    def get_hotel_recommendations(
            self,
            city: str,
            attractions: List[Dict],
            checkin_date: str,
            checkout_date: str,
            budget_range: tuple = (50, 300),
            currency: str = "USD",
            min_review_score: float = 7.0,
            preferred_star_classes: Optional[List[int]] = None,
            use_agent: bool = True
    ) -> dict:
        """Rekomendacje hoteli na podstawie atrakcji i preferencji"""
        # print("DEBUG ATTRACTINS AGENT  !!!!!!!!!!!!!!!!!!!!!!!!")
        # print(attractions)
        print(f"🎯 Szukam rekomendacji dla {city} z {len(attractions)} atrakcjami")

        raw_data = self.search_hotels(
            city=city,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            min_price=budget_range[0],
            max_price=budget_range[1],
            currency=currency,
            star_classes=preferred_star_classes,
            min_review_score=min_review_score,
            max_hotels=10,
            attractions=attractions,
            use_agent=use_agent
        )

        formatter = GenericLLMFormatter(
            llm=self.llm,
            prompt_template_str=self.prompts["hotel_json_formatter_template"],
            input_variables=["raw_data", "city"]
        )

        json_data = formatter.run(
            raw_data=raw_data,
            city=city
        )

        return json_data

