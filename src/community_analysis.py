import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Użycie backendu nieinteraktywnego (do zapisu plików png)
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from neo4j import GraphDatabase

# Konfiguracja bazy Neo4j
URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
USER = "neo4j"
PASSWORD = "password"

# Folder na wygenerowane wykresy
OUT_DIR = "wykresy_spolecznosci"
os.makedirs(OUT_DIR, exist_ok=True)

class SteamNetworkAnalyzer:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return pd.DataFrame([r.values() for r in result], columns=result.keys())

    def execute_write(self, query, parameters=None):
        with self.driver.session() as session:
            session.run(query, parameters)

    def prepare_gds_projection(self):
        print("[1/5] Usuwanie starej projekcji GDS (jeśli istnieje)...")
        self.execute_write("CALL gds.graph.drop('filtered_games', false) YIELD graphName")
        
        print("[2/5] Tworzenie przefiltrowanej projekcji grafu (shared_players > 50, jaccard > 0.05)...")
        # Filtrujemy szum, żeby algorytm społeczności nie zwariował na włochatej kuli (hairball)
        query = """
        CALL gds.graph.project.cypher(
          'filtered_games',
          'MATCH (n:Game) RETURN id(n) AS id',
          'MATCH (n:Game)-[r:SIMILAR]->(m:Game) 
           WHERE r.shared_players > 50 AND r.jaccard > 0.05 
           RETURN id(n) AS source, id(m) AS target, r.jaccard AS weight'
        )
        """
        self.execute_write(query)
        print("Projekcja GDS gotowa.")

    def run_louvain(self):
        print("[3/5] Uruchamianie algorytmu Louvain i zapis wyników do bazy...")
        query = """
        CALL gds.louvain.write('filtered_games', {
          relationshipWeightProperty: 'weight',
          writeProperty: 'community_id'
        })
        YIELD communityCount, modularity
        RETURN communityCount, modularity
        """
        res = self.run_query(query)
        print(f"Wykryto klastrów: {res['communityCount'][0]}, Modularity: {res['modularity'][0]:.4f}")

    def plot_community_sizes(self):
        print("[4/5] Generowanie wykresu top 10 największych społeczności...")
        query = """
        MATCH (g:Game)
        WHERE g.community_id IS NOT NULL
        RETURN g.community_id AS community, count(g) AS size
        ORDER BY size DESC
        LIMIT 10
        """
        df = self.run_query(query)
        
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df, x='community', y='size', order=df['community'], palette='viridis')
        plt.title('Top 10 Największych Społeczności Gier na Steam (Wg zachowań graczy)')
        plt.xlabel('ID Społeczności')
        plt.ylabel('Liczba Gier w Klastrze')
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/1_top_10_communities.png", dpi=300)
        plt.close()
        print(f"Zapisano: {OUT_DIR}/1_top_10_communities.png")

    def plot_genres_per_community(self, top_n=5):
        print(f"Generowanie wykresu najczęstszych gatunków dla top {top_n} społeczności...")
        # To zapytanie rozbija tagi genres po | i liczy ich wystąpienia w każdej z dużych społeczności
        query = f"""
        MATCH (g:Game)
        WHERE g.community_id IS NOT NULL
        WITH g.community_id AS community, count(g) AS size
        ORDER BY size DESC LIMIT {top_n}
        
        MATCH (g:Game)
        WHERE g.community_id = community AND g.genres IS NOT NULL
        UNWIND split(g.genres, '|') AS genre
        WITH community, genre, count(*) AS count
        ORDER BY count DESC
        WITH community, collect({{genre: genre, count: count}})[0..5] AS top_genres
        UNWIND top_genres AS tg
        RETURN community, tg.genre AS genre, tg.count AS count
        """
        df = self.run_query(query)
        
        plt.figure(figsize=(14, 8))
        sns.barplot(data=df, x='community', y='count', hue='genre', palette='tab20')
        plt.title('Najpopularniejsze oficjalne gatunki wewnątrz wykrytych społeczności')
        plt.xlabel('ID Społeczności')
        plt.ylabel('Suma wystąpień gatunku')
        plt.legend(title='Gatunek', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/2_genres_per_community.png", dpi=300)
        plt.close()
        print(f"Zapisano: {OUT_DIR}/2_genres_per_community.png")

    def visualize_network_sample(self):
        print("[5/5] Generowanie wizualizacji krawędzi dla największych społeczności...")
        # Pobieramy próbkę tylko najsilniejszych krawędzi wewnątrz topowych baniek by graf był czytelny na rysunku
        query = """
        MATCH (g:Game) WHERE g.community_id IS NOT NULL
        WITH g.community_id AS community, count(g) AS size ORDER BY size DESC LIMIT 4
        WITH collect(community) AS top_communities
        
        MATCH (n:Game)-[r:SIMILAR]->(m:Game)
        WHERE n.community_id IN top_communities AND m.community_id IN top_communities
          AND n.community_id = m.community_id
          AND r.shared_players > 1000 AND r.jaccard > 0.15
        RETURN n.name AS source, m.name AS target, n.community_id AS community
        LIMIT 1500
        """
        df = self.run_query(query)
        if df.empty:
            print("Zbyt mocne filtry do wizualizacji - brak krawędzi spełniających jaccard > 0.15 i shared > 1000.")
            return

        G = nx.from_pandas_edgelist(df, 'source', 'target')
        
        color_map = {}
        for _, row in df.iterrows():
            color_map[row['source']] = row['community']
            color_map[row['target']] = row['community']
            
        colors = [color_map.get(node, 0) for node in G.nodes()]
        
        plt.figure(figsize=(16, 16))
        pos = nx.spring_layout(G, k=0.15, iterations=50)
        nx.draw(G, pos, node_color=colors, cmap=plt.cm.Set2, with_labels=False, 
                node_size=40, edge_color='#CCCCCC', alpha=0.8)
        
        plt.title("Wizualizacja Podgrafu - Klastry Gier Steam (Silne połączenia > 1000 graczy)")
        plt.tight_layout()
        plt.savefig(f"{OUT_DIR}/3_network_visualization.png", dpi=300, facecolor='black')
        plt.close()
        print(f"Zapisano: {OUT_DIR}/3_network_visualization.png")

def main():
    print("Rozpoczynanie kompleksowej analizy społeczności...")
    analyzer = SteamNetworkAnalyzer(URI, USER, PASSWORD)
    try:
        analyzer.prepare_gds_projection()
        analyzer.run_louvain()
        analyzer.plot_community_sizes()
        analyzer.plot_genres_per_community()
        analyzer.visualize_network_sample()
        print("Analiza zakończona sukcesem! Sprawdź wygenerowane pliki PNG.")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
