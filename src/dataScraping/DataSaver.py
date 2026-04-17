import csv
import threading
from queue import Queue
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dataScraping.dataScraper import DataScraper

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
EDGES_FILE = os.path.join(DATA_DIR, 'edges.csv')
NODES_FILE = os.path.join(DATA_DIR, 'nodes.csv')

data_queue = Queue()

def csv_writer_worker():
    """Wątek konsumenta: pobiera dane z kolejki i zapisuje do CSV."""
    
    with open(EDGES_FILE, 'w', newline='', encoding='utf-8') as f_edges, \
         open(NODES_FILE, 'w', newline='', encoding='utf-8') as f_nodes:
        
        edges_writer = csv.writer(f_edges)
        nodes_writer = csv.writer(f_nodes)
        
        edges_writer.writerow(['source', 'target', 'type', 'weight'])
        nodes_writer.writerow(['id', 'node_type'])
        
        seen_nodes = set()
        
        while True:
            record = data_queue.get()
            
            if record is None:
                break
                
            if record['type'] == 'friend':
                edges_writer.writerow([record['source'], record['target'], 'friend', ''])
                
                if record['source'] not in seen_nodes:
                    nodes_writer.writerow([record['source'], 'user'])
                    seen_nodes.add(record['source'])
                if record['target'] not in seen_nodes:
                    nodes_writer.writerow([record['target'], 'user'])
                    seen_nodes.add(record['target'])
                    
            elif record['type'] == 'game':
                game_node = f"App_{record['app_id']}"
                
                edges_writer.writerow([record['steam_id'], game_node, 'game', record['playtime']])
                
                if record['steam_id'] not in seen_nodes:
                    nodes_writer.writerow([record['steam_id'], 'user'])
                    seen_nodes.add(record['steam_id'])
                if game_node not in seen_nodes:
                    nodes_writer.writerow([game_node, 'game'])
                    seen_nodes.add(game_node)
                    
            data_queue.task_done()

def run_scraper_to_csv(seed_id, max_records=500):
    """Główna funkcja uruchamiająca proces."""
    
    writer_thread = threading.Thread(target=csv_writer_worker)
    writer_thread.start()
    
    scraper = DataScraper(seed_id, is_test=True)
    
    counter = 0
    print(f"Rozpoczynam pobieranie danych dla Seed ID: {seed_id}")
    
    for record in scraper.run():
        if counter >= max_records:
            break
            
        data_queue.put(record)
        counter += 1
        
        if counter % 50 == 0:
            print(f"Pobrano {counter} rekordów...")

    data_queue.put(None)
    data_queue.join()
    writer_thread.join()
    
    print(f"Zakończono. Zapisano {counter} rekordów w folderze data/")

if __name__ == "__main__":
    run_scraper_to_csv("76561198154174120", max_records=200)