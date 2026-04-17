import yaml
import requests
from collections import deque
import os
import threading
class DataScraper:
    def __init__(self, starting_seed_steam_id, is_test=False):
        self.seed_id = starting_seed_steam_id
        self.is_test = is_test
        self.api_key = self._load_api_key()

    def _load_api_key(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, 'secrets.yaml')

        with open(yaml_path, 'r') as file:
            secrets = yaml.safe_load(file)
            return secrets['STEAM_API_KEY']

    def _get_friends(self, steam_id):
        url = f"http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={self.api_key}&steamid={steam_id}&relationship=friend"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return [f['steamid'] for f in response.json().get('friendslist', {}).get('friends', [])]
        except:
            pass
        return []

    def _get_games(self, steam_id):
        url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&format=json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json().get('response', {}).get('games', [])
        except:
            pass
        return []

    def run(self):
        queue = deque([(self.seed_id, 0)])
        visited = set([self.seed_id])

        while queue:
            current_user, depth = queue.popleft()

            if self.is_test and depth > 1:
                continue

            games = self._get_games(current_user)
            if games:
                for game in games:
                    yield {
                        'type': 'game',
                        'steam_id': current_user,
                        'app_id': game['appid'],
                        'playtime': game['playtime_forever']
                    }

            friends = self._get_friends(current_user)
            for friend in friends:
                yield {
                    'type': 'friend',
                    'source': current_user,
                    'target': friend
                }
                if friend not in visited:
                    visited.add(friend)
                    queue.append((friend, depth + 1))


