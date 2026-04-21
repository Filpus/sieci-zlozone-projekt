from flask_login import current_user
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
            url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&format=json&include_appinfo=1&include_played_free_games=1"
            try:
                response = requests.get(url, timeout=20)
                if response.status_code == 200:
                    data = response.json().get('response', {})
                    if 'games' in data:
                        return data['games']
                    return []
                else:
                    # To powie Ci Prawdę o tym, co robi Steam
                    print(f"[STATUS {response.status_code}] Odmowa dla ID: {steam_id}")
                    return []
            except Exception as e:
                print(f"Wyjątek połączenia przy grach: {e}")
                return []

    def run(self):
        queue = deque([(self.seed_id, 0)])
        visited = set([self.seed_id])

        while queue:
            current_user, depth = queue.popleft()

            if self.is_test and depth > 1:
                continue

            games = self._get_games(current_user)
            if not games:
                print(f"[Odrzucono] Profil prywatny odciął ścieżkę: {current_user}")
                continue # Przechodzi do nastepnego w kolejce bez dodawania znajomych
                
            # Zapisz gry do kolejki
            for game in games:
                yield {
                    'type': 'game',
                    'steam_id': current_user,
                    'app_id': game['appid'],
                    'playtime': game.get('playtime_forever', 0),
                    'name': game.get('name', 'Unknown')
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


