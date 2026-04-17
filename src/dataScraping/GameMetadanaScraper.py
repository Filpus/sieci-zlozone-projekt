import requests
import time
import csv
import os

class GameMetadataScraper:
    def __init__(self, output_file="game_metadata.csv"):
        self.output_file = output_file
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['app_id', 'name', 'type', 'developer', 'genres'])

    def fetch_game_data(self, app_id):
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                app_str = str(app_id)
                if data and app_str in data and data[app_str].get('success'):
                    game_info = data[app_str]['data']
                    
                    name = game_info.get('name', 'Unknown')
                    app_type = game_info.get('type', 'Unknown')
                    
                    developers = game_info.get('developers', [])
                    dev_str = developers[0] if developers else 'Unknown'
                    
                    genres = game_info.get('genres', [])
                    genres_list = [g['description'] for g in genres]
                    genres_str = "|".join(genres_list)
                    
                    return [app_id, name, app_type, dev_str, genres_str]
        except Exception as e:
            print(f"Błąd dla App ID {app_id}: {e}")
            
        return None

    def run(self, app_ids_list):
        print(f"Rozpoczynam pobieranie metadanych dla {len(app_ids_list)} gier...")
        
        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            for index, app_id in enumerate(app_ids_list):
                clean_id = str(app_id).replace("App_", "")
                
                data = self.fetch_game_data(clean_id)
                if data:
                    writer.writerow(data)
                    print(f"[{index+1}/{len(app_ids_list)}] Zapisano: {data[1]}")
                else:
                    print(f"[{index+1}/{len(app_ids_list)}] Brak danych dla ID: {clean_id}")
                
                time.sleep(1.5)

if __name__ == "__main__":
    my_chunk_of_games = [730, 570, 400, 105600] 
    
    scraper = GameMetadataScraper("my_part_metadata.csv")
    scraper.run(my_chunk_of_games)