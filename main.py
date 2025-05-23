import json
from agents.map_agent import MapAgent
from agents.attraction_agent import AttractionAgent

if __name__ == "__main__":
    # with open("data/input.json") as f:
    #     data = json.load(f)

    agent = MapAgent()
    warsaw_attractions = [
        "Old Town Market Square",
        "Royal Castle",
        "Lazienki Park",
        "Wilanów Palace",
        "POLIN Museum of the History of Polish Jews",
        "Palace of Culture and Science",
        "Warsaw Uprising Museum",
        "Copernicus Science Centre",
        "Krakowskie Przedmieście",
        "Złote Tarasy Shopping Mall",
        "Praga District",
        "Saxon Garden",
        "National Museum",
        "Vistula Boulevards",
        "Neon Museum"
    ]
    response = agent.optimize("Warsaw", 3, "PJATK", warsaw_attractions)

    # print(agent.get_eta("Warsaw","Royal Castle", "PJATK", "walking"))
    