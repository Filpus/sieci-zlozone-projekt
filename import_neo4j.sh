#!/bin/bash
set -e

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

echo "Trwa generowanie mniejszych plików dla różnych progów (SIMILAR_LOW, MED, HIGH) za pomocą awk..."
echo "To zajmie około 2-3 minuty na szybkim dysku..."
awk -F',' '$3 > 10 && $4 > 0.01' data/edges_data.csv > data/edges_low.csv
awk -F',' '$3 > 50 && $4 > 0.05' data/edges_data.csv > data/edges_med.csv
awk -F',' '$3 > 200 && $4 > 0.1' data/edges_data.csv > data/edges_high.csv

echo "Rozpoczynam import wsadowy wielu typów relacji. To zajmie od 5 do 15 minut..."
docker-compose run --rm neo4j neo4j-admin database import full neo4j \
    --nodes=Game=/import/game_metadata.csv \
    --relationships=SIMILAR=/import/edges_header.csv,/import/edges_data.csv \
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
