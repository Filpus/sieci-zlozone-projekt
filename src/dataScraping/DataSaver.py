import csv
import threading
import os
from queue import Queue
import pandas as pd
from dataScraping.dataScraper import DataScraper

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
EDGES_FILE = os.path.join(DATA_DIR, 'edges.csv')
NODES_FILE = os.path.join(DATA_DIR, 'nodes.csv')

data_queue = Queue()

def csv_writer_worker():
    file_exists = os.path.isfile(EDGES_FILE)
    
    with open(EDGES_FILE, 'a', newline='', encoding='utf-8') as f_edges, \
         open(NODES_FILE, 'a', newline='', encoding='utf-8') as f_nodes:
        
        edges_writer = csv.writer(f_edges)
        nodes_writer = csv.writer(f_nodes)
        
        if not file_exists:
            edges_writer.writerow(['source', 'target', 'type', 'weight'])
            nodes_writer.writerow(['id', 'node_type'])
        
        seen_nodes = set()
        if os.path.isfile(NODES_FILE):
            try:
                existing_nodes = pd.read_csv(NODES_FILE)
                seen_nodes.update(existing_nodes['id'].astype(str).tolist())
            except:
                pass

        while True:
            record = data_queue.get()
            if record is None:
                data_queue.task_done()
                break
                
            if record['type'] == 'friend':
                edges_writer.writerow([record['source'], record['target'], 'friend', ''])
                
                if str(record['source']) not in seen_nodes:
                    nodes_writer.writerow([record['source'], 'user'])
                    seen_nodes.add(str(record['source']))
                if str(record['target']) not in seen_nodes:
                    nodes_writer.writerow([record['target'], 'user'])
                    seen_nodes.add(str(record['target']))
                    
            elif record['type'] == 'game':
                game_node = f"App_{record['app_id']}"
                edges_writer.writerow([record['steam_id'], game_node, 'game', record['playtime']])
                
                if str(record['steam_id']) not in seen_nodes:
                    nodes_writer.writerow([record['steam_id'], 'user'])
                    seen_nodes.add(str(record['steam_id']))
                if game_node not in seen_nodes:
                    nodes_writer.writerow([game_node, 'game'])
                    seen_nodes.add(game_node)
            
            f_edges.flush()
            f_nodes.flush()
            data_queue.task_done()

def run_snowball_to_csv(seed_id, max_records):
    initial_visited = set()
    frontier = set()
    if os.path.isfile(EDGES_FILE):
        try:
            print("Wczytywanie istniejacych danych...")
            df = pd.read_csv(EDGES_FILE, dtype=str)
            initial_visited.update(df['source'].unique())
            print(f"Pominietych zostanie {len(initial_visited)} juz pobranych wezlow.")
            
            friend_edges = df[df['type'] == 'friend']
            if not friend_edges.empty:
                known_friends = set(friend_edges['target'].unique())
                frontier = known_friends - initial_visited
                print(f"Wykryto {len(frontier)} znajomych w kolejce z poprzedniej sesji.")
        except Exception as e:
            print(f"Blad wczytywania bazy: {e}")

    writer_thread = threading.Thread(target=csv_writer_worker, daemon=True)
    writer_thread.start()
    
    scraper = DataScraper(seed_id, is_test=False)
    scraper.visited.update(initial_visited)
    scraper.frontier = list(frontier)

    counter = 0
    try:
        for record in scraper.run():
            if counter >= max_records:
                break
            
            data_queue.put(record)
            counter += 1
            
            if counter % 100 == 0:
                print(f"Status: Zapisano {counter} nowych krawedzi...")
    except KeyboardInterrupt:
        print("\nPrzerwano recznie. Trwa bezpieczne zapisywanie...")
    finally:
        data_queue.put(None)
        data_queue.join()
        writer_thread.join()
        print(f"Zakonczono. Dodano {counter} rekordow.")