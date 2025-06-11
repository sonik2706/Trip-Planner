from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import List, Dict
import json

from langchain_google_genai import ChatGoogleGenerativeAI


class LocationNormalizer:
    def __init__(self, config):
        self.config = config
        self._setup_llm()
        self.prompt_template = PromptTemplate(
            template=(
                "Given a list of location names, return a valid JSON object where each key is the original name "
                "and each value is the most concise, accurate local name that would work best for OpenStreetMap search.\n\n"
                "Avoid generic words like 'bazaar', 'fountain', and translations. Do not include the city name. "
                "Focus on names that OpenStreetMap would likely recognize.\n\n"
                "Examples:\n"
                "- 'Sarajevo City Hall (Vijećnica)' → 'Vijećnica'\n"
                "- 'Baščaršija Bazaar' → 'Baščaršija'\n"
                "- 'Sebilj Brunnen (Fountain)' → 'Sebilj'\n"
                "- 'Tunnel of Hope – War Tunnel' → 'Tunnel of Hope'\n"
                "- 'Latin Bridge' → 'Latin Bridge'\n"
                "- 'Gazi Husrev-beg Mosque' → 'Gazi Husrev-beg Mosque'\n\n"
                "Input:\n{raw_names}\n\n"
                "Return ONLY a valid JSON dictionary in the format: {{\"original_name\": \"normalized_name\", ...}}."
            ),
            input_variables=["raw_names"]
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)

    def _setup_llm(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.config.GEMINI_API_KEY,
            temperature=0.3,
            top_k=40,
            top_p=0.95,
            verbose=True,
        )

    def normalize(self, raw_name: str) -> str:
        """Normalize a single location name."""
        result = self.normalize_all([raw_name])
        return result.get(raw_name, raw_name)

    def normalize_all(self, raw_names: List[str]) -> Dict[str, str]:
        """Normalize a list of location names using LLM. Returns a dict: original_name -> normalized_name."""
        if not raw_names:
            return {}

        # Prepare names as bullet list
        names_text = "\n".join(f"- {name}" for name in raw_names)

        try:
            response = self.chain.invoke({"raw_names": names_text})

            # Sprawdzamy czy response to dict czy string
            if isinstance(response, dict):
                response_text = response.get('text', str(response))
            else:
                response_text = str(response)

            response_text = response_text.strip()
            print(f"[LLM RAW RESPONSE]\n{response_text}")

            # Znajdź pierwszy i ostatni nawias klamrowy
            start = response_text.find("{")
            end = response_text.rfind("}") + 1

            if start == -1 or end == 0:
                raise ValueError("Brak poprawnych nawiasów klamrowych w odpowiedzi")

            json_substring = response_text[start:end]
            print(f"[JSON SUBSTRING]\n{json_substring}")

            data = json.loads(json_substring)

            # Zabezpieczenie — tylko znane wejściowe klucze
            result = {}
            for name in raw_names:
                if name in data:
                    result[name] = data[name]
                else:
                    # Spróbuj znaleźć podobny klucz (case-insensitive)
                    found = False
                    for key in data.keys():
                        if key.lower() == name.lower():
                            result[name] = data[key]
                            found = True
                            break
                    if not found:
                        result[name] = name  # fallback

            return result

        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            print(f"[ERROR] Failed to parse LLM response: {e}")
            print(f"[ERROR] Raw response type: {type(response)}")
            if 'response' in locals():
                print(f"[ERROR] Raw response content: {response}")
            return {name: name for name in raw_names}  # fallback