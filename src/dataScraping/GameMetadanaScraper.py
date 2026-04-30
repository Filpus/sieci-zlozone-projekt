import requests
import time
import csv
import os

class GameMetadataScraper:
    def __init__(self, output_file="game_metadata.csv"):
        self.output_file = output_file
        self.scraped_ids = set()
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'name', 'type', 'developer', 'genres'])
        else:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row:
                        self.scraped_ids.add(row[0])

    def fetch_game_data(self, original_id, clean_id):
        url = f"https://store.steampowered.com/api/appdetails?appids={clean_id}"
        
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 429:
                return "RATE_LIMIT"
                
            if response.status_code == 200:
                data = response.json()
                
                if data and clean_id in data and data[clean_id].get('success'):
                    game_info = data[clean_id]['data']
                    
                    name = game_info.get('name', 'Unknown')
                    app_type = game_info.get('type', 'Unknown')
                    
                    developers = game_info.get('developers', [])
                    dev_str = developers[0] if developers else 'Unknown'
                    
                    genres = game_info.get('genres', [])
                    genres_list = [g['description'] for g in genres]
                    genres_str = "|".join(genres_list)
                    
                    return [original_id, name, app_type, dev_str, genres_str]
        except Exception:
            pass
            
        return None

    def run_from_file(self, input_csv_path):
        print(f"Skanowanie pliku wejsciowego: {input_csv_path}...")
        
        games_to_scrape = []
        
        with open(input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            id_idx = 0
            if header:
                for i, col_name in enumerate(header):
                    if col_name.strip() == 'id':
                        id_idx = i
                        break
                        
            for row in reader:
                if not row or len(row) <= id_idx:
                    continue
                    
                node_id = row[id_idx].strip()
                
                if node_id.startswith("App_"):
                    games_to_scrape.append(node_id)
        
        games_to_scrape = list(dict.fromkeys(games_to_scrape))
        total_games = len(games_to_scrape)
        
        print(f"Odfiltrowano {total_games} unikalnych gier do sprawdzenia.")

        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            for index, original_id in enumerate(games_to_scrape):
                if original_id in self.scraped_ids:
                    continue
                    
                clean_id = original_id.replace("App_", "")
                
                data = self.fetch_game_data(original_id, clean_id)
                
                if data == "RATE_LIMIT":
                    print("Blokada API (HTTP 429). Czekam 60 sekund...")
                    time.sleep(60)
                    data = self.fetch_game_data(original_id, clean_id)
                    if data == "RATE_LIMIT":
                        print("Dalsza blokada. Przerywam dzialanie skryptu.")
                        break
                        
                if data and data != "RATE_LIMIT":
                    writer.writerow(data)
                    f.flush()
                    self.scraped_ids.add(original_id)
                    print(f"[{index+1}/{total_games}] Zapisano: {data[1]}")
                else:
                    print(f"[{index+1}/{total_games}] Brak danych dla: {original_id}")
                    
                time.sleep(1.5)

if __name__ == "__main__":
    INPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'nodes-Copy1.csv')
    OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'game_metadata.csv')
    
    scraper = GameMetadataScraper(OUTPUT_FILE)
    scraper.run_from_file(INPUT_FILE)