import csv
import math
import sqlite3
import os
from collections import Counter, defaultdict
from itertools import combinations

def generate_out_of_core_projection(input_file, output_file, db_file="temp_edges.db"):
    print("ETAP 1: Skanowanie bazy i zapisywanie bibliotek (Tylko czyste dane w RAM)...")
    
    user_games = defaultdict(list)
    game_popularity = Counter()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        
        src_idx, tgt_idx, type_idx, weight_idx = 0, 1, 2, 3
        for i, col in enumerate(header):
            if col.strip() == 'source': src_idx = i
            elif col.strip() == 'target': tgt_idx = i
            elif col.strip() == 'type': type_idx = i
            elif col.strip() == 'weight': weight_idx = i

        for row in reader:
            if len(row) <= max(src_idx, tgt_idx, type_idx, weight_idx): continue
            
            if row[type_idx].strip() == 'game':
                source = row[src_idx].strip()
                target = row[tgt_idx].strip()
                
                try:
                    weight = float(row[weight_idx].strip())
                    if weight > 0:
                        user_games[source].append(target)
                        game_popularity[target] += 1
                except ValueError:
                    pass

    print(f"Zaladowano {len(user_games)} aktywnych graczy do RAM-u.")

    # --- KONFIGURACJA SQLITE (Tymczasowy bufor na dysku) ---
    print("ETAP 2: Tworzenie tymczasowej bazy danych na dysku...")
    if os.path.exists(db_file):
        os.remove(db_file)
        
    conn = sqlite3.connect(db_file)
    # Ekstremalne przyspieszenie zapisu do pliku:
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("CREATE TABLE edges (game_A TEXT, game_B TEXT, ra_penalty REAL)")
    
    print("ETAP 3: Generowanie kombinacji i strumieniowanie na dysk...")
    total_users = len(user_games)
    batch = []
    BATCH_SIZE = 250000 # Ile krawedzi trzymamy w RAM przed zrzutem
    
    for i, (user, games) in enumerate(user_games.items(), 1):
        degree = len(games)
        if degree > 1:
            games.sort()
            ra_penalty = 1.0 / degree
            
            for pair in combinations(games, 2):
                batch.append((pair[0], pair[1], ra_penalty))
                
                if len(batch) >= BATCH_SIZE:
                    conn.executemany("INSERT INTO edges VALUES (?, ?, ?)", batch)
                    batch = []
                    
        if i % 2000 == 0:
            print(f"Przetworzono i zrzucono graczy: {i}/{total_users}")
            
    # Zrzut resztki, ktora zostala w buforze
    if batch:
        conn.executemany("INSERT INTO edges VALUES (?, ?, ?)", batch)
        
    print("Kombinacje zapisane! Oczekiwanie na SQL (grupowanie milionow wierszy)...")
    
    # --- AGREGACJA BAZODANOWA ---
    print("ETAP 4: Obliczanie ulamkow i zrzut do docelowego CSV...")
    
    query = """
        SELECT game_A, game_B, COUNT(*) as co_players, SUM(ra_penalty) as ra_score
        FROM edges 
        GROUP BY game_A, game_B 
        HAVING COUNT(*) > 1
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    saved_edges = 0
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'source', 'target', 'shared_players', 
            'jaccard', 'overlap', 'cosine', 'resource_allocation'
        ])
        
        # Pobieramy zagregowane wiersze partiami (fetchmany), by nie zapchac RAMu
        while True:
            rows = cursor.fetchmany(10000)
            if not rows:
                break
                
            for row in rows:
                game_A, game_B, co_players, ra_score = row
                pop_A = game_popularity[game_A]
                pop_B = game_popularity[game_B]
                
                union_size = pop_A + pop_B - co_players
                jaccard = co_players / union_size
                overlap = co_players / min(pop_A, pop_B)
                cosine = co_players / math.sqrt(pop_A * pop_B)
                
                writer.writerow([
                    game_A, game_B, 
                    co_players, 
                    round(jaccard, 6), round(overlap, 6), round(cosine, 6), round(ra_score, 6)
                ])
                saved_edges += 1
                
    conn.close()
    
    # Sprzatanie po sobie
    if os.path.exists(db_file):
        os.remove(db_file)
        
    print(f"ZAKONCZONE SUKCESEM. Zapisano {saved_edges} krawedzi do {output_file}.")

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    INPUT_FILE = os.path.join(base_dir, '..', 'data', 'edges-Copy1.csv')
    OUTPUT_FILE = os.path.join(base_dir, '..', 'data', 'game_game_rich_projection.csv')
    
    generate_out_of_core_projection(INPUT_FILE, OUTPUT_FILE)