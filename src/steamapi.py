import requests
import json
from dotenv import load_dotenv

load_dotenv()


class SteamAPI:
    def __init__(self, API_KEY):
        self.API_KEY = API_KEY

    def get_games(self, steamid):
        req = requests.get(
            f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.API_KEY}&steamid={steamid}"
        )
        if req.status_code != 200:
            return []

        games = json.loads(req.text)["response"]
        if games:
            return games["games"]
        else:
            return []

    def get_steam_id(self, username):
        req = requests.get(
            f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.API_KEY}&vanityurl={username}"
        )
        if req.status_code != 200:
            return []

        return json.loads(req.text)["response"]["steamid"]

    def get_app_list(self):
        req = requests.get("http://api.steampowered.com/ISteamApps/GetAppList/v2/")
        if req.status_code != 200:
            return []
        else:
            return json.loads(req.text)["applist"]["apps"]

    def get_games_by_id(self, appid):
        req = requests.get(
            f"http://store.steampowered.com/api/appdetails?appids={appid}"
        )
        if req.status_code != 200:
            return []
        else:
            return json.loads(req.text)[str(appid)]["data"]
