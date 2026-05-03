#!/bin/bash
set -e

# Ścieżka do pliku wejściowego. Domyślnie używa starego edges_data.csv
INPUT_FILE=${1:-"data/edges_data.csv"}

echo "--- ROZPOCZYNAM IMPORT ---"
echo "Używam pliku z krawędziami: $INPUT_FILE"

# Zastopuj ewentualny uruchomiony kontener
echo "Zatrzymywanie kontenerów (jeśli są uruchomione)..."
docker-compose stop neo4j

# Wyczyść poprzednią bazę na wolumenie (Neo4j Community pozwala tylko na 1 bazę o nazwie neo4j)
echo "Czyszczenie poprzedniej bazy..."
docker-compose run --rm neo4j bash -c 'rm -rf /data/databases/neo4j /data/transactions/neo4j'

# Edycja nagłówka dla węzłów
echo "Przygotowanie nagłówków..."
sed -i '1s/.*/id:ID,name,type,developer,genres/' data/game_metadata.csv

# Utworzenie osobnego pliku nagłówka dla krawędzi
echo ":START_ID,:END_ID,shared_players:int,jaccard:float,overlap:float,cosine:float,resource_allocation:float" > data/edges_header.csv

echo "Przygotowywanie pliku krawędzi do importu (usuwanie tekstowego nagłówka jeśli istnieje)..."
if head -n 1 "$INPUT_FILE" | grep -q "source"; then
    tail -n +2 "$INPUT_FILE" > data/current_edges.csv
else
    cp "$INPUT_FILE" data/current_edges.csv
fi

echo "Trwa generowanie mniejszych plików dla różnych progów (SIMILAR_LOW, MED, HIGH) za pomocą awk..."
echo "Filtrowanie TYLKO po shared_players (neutralne metryka-wise)..."
awk -F',' '$3 > 10' data/current_edges.csv > data/edges_low.csv
awk -F',' '$3 > 50' data/current_edges.csv > data/edges_med.csv
awk -F',' '$3 > 200' data/current_edges.csv > data/edges_high.csv

echo "Rozpoczynam import wsadowy wielu typów relacji. To zajmie od 5 do 15 minut..."
docker-compose run --rm neo4j neo4j-admin database import full neo4j \
    --nodes=Game=/import/game_metadata.csv \
    --relationships=SIMILAR=/import/edges_header.csv,/import/current_edges.csv \
    --relationships=SIMILAR_LOW=/import/edges_header.csv,/import/edges_low.csv \
    --relationships=SIMILAR_MED=/import/edges_header.csv,/import/edges_med.csv \
    --relationships=SIMILAR_HIGH=/import/edges_header.csv,/import/edges_high.csv \
    --skip-bad-relationships \
    --bad-tolerance=100000000 \
    --skip-duplicate-nodes \
    --overwrite-destination

echo "Import zakończony! Uruchamianie bazy Neo4j..."
docker-compose up -d neo4j

echo "Gotowe! Baza wkrótce wstanie i będzie gotowa pod http://localhost:7474"
