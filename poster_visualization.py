"""
Wizualizacja wykrytych społeczności gier Steam na poster naukowy.
Uruchom: python poster_visualization.py
"""

import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from collections import Counter
from neo4j import GraphDatabase

# --- Połączenie z Neo4j ---
driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

def run_query(q):
    with driver.session() as s:
        result = s.run(q)
        return pd.DataFrame([r.data() for r in result])

# --- KONFIGURACJA ---
COMMUNITY_PROP = "comm_high_jaccard_3_0"
REL_TYPE = "SIMILAR_HIGH"
TOP_N_CLUSTERS = 6
MAX_GAMES_PER_CLUSTER = 12

# --- 1. Pobierz top klastry ---
print("Pobieram klastry z Neo4j...")
q_clusters = f"""
MATCH (g:Game)
WHERE g.{COMMUNITY_PROP} IS NOT NULL AND apoc.node.degree(g, '{REL_TYPE}') > 0
WITH g.{COMMUNITY_PROP} AS community, count(g) AS size
WHERE size >= 5
RETURN community, size
ORDER BY size DESC
LIMIT {TOP_N_CLUSTERS}
"""
df_clusters = run_query(q_clusters)
cluster_ids = df_clusters['community'].tolist()
print(f"Znaleziono {len(cluster_ids)} klastrów: {list(zip(df_clusters['community'], df_clusters['size']))}")

# --- 2. Pobierz gry i krawędzie ---
G = nx.Graph()
cluster_names = {}

for idx, cid in enumerate(cluster_ids):
    q_games = f"""
    MATCH (g:Game)
    WHERE g.{COMMUNITY_PROP} = {cid} AND g.name IS NOT NULL
    RETURN g.name AS name, g.genres AS genres, elementId(g) AS eid
    LIMIT {MAX_GAMES_PER_CLUSTER}
    """
    df_games = run_query(q_games)

    all_genres = []
    for genres_str in df_games['genres'].dropna():
        all_genres.extend(genres_str.split('|'))
    top_genre = Counter(all_genres).most_common(1)[0][0] if all_genres else "Unknown"
    cluster_names[cid] = f"Klaster {idx+1}: {top_genre} ({len(df_games)} gier)"

    for _, row in df_games.iterrows():
        short_name = row['name'][:28] + "…" if len(row['name']) > 28 else row['name']
        G.add_node(row['eid'], label=short_name, cluster=idx, cluster_id=cid)

    eids = df_games['eid'].tolist()
    if len(eids) > 1:
        q_edges = f"""
        MATCH (a:Game)-[:{REL_TYPE}]-(b:Game)
        WHERE a.{COMMUNITY_PROP} = {cid} AND b.{COMMUNITY_PROP} = {cid}
          AND elementId(a) < elementId(b)
        RETURN elementId(a) AS src, elementId(b) AS tgt
        LIMIT 100
        """
        df_edges = run_query(q_edges)
        # Zachowaj tylko krawędzie między wczytanymi węzłami
        eid_set = set(eids)
        for _, e in df_edges.iterrows():
            if e['src'] in eid_set and e['tgt'] in eid_set:
                G.add_edge(e['src'], e['tgt'])

print(f"Graf: {G.number_of_nodes()} węzłów, {G.number_of_edges()} krawędzi")

# --- 3. Wizualizacja ---
plt.style.use('dark_background')
fig = plt.figure(figsize=(20, 16))

colors_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#C9B1FF',
                   '#F7DC6F', '#82E0AA', '#F0B27A', '#AED6F1']

node_colors = [colors_palette[G.nodes[n].get('cluster', 0) % len(colors_palette)] for n in G.nodes()]
labels = {n: G.nodes[n].get('label', str(n)) for n in G.nodes()}

# Layout — każdy klaster osobno w gridzie
pos = {}
cols = 3

for idx, cid in enumerate(cluster_ids):
    cluster_nodes = [n for n in G.nodes() if G.nodes[n].get('cluster_id') == cid]
    subG = G.subgraph(cluster_nodes)

    cx = (idx % cols) * 6
    cy = -(idx // cols) * 6

    if len(cluster_nodes) > 1:
        sub_pos = nx.spring_layout(subG, k=1.5, iterations=50, seed=42)
    else:
        sub_pos = {cluster_nodes[0]: (0, 0)}

    for node, (x, y) in sub_pos.items():
        pos[node] = (cx + x * 2, cy + y * 2)

nx.draw_networkx_edges(G, pos, alpha=0.15, edge_color='#666666', width=0.5)
nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=300,
                        edgecolors='white', linewidths=0.5, alpha=0.9)
nx.draw_networkx_labels(G, pos, labels, font_size=6, font_color='white',
                         font_weight='bold')

legend_patches = [mpatches.Patch(color=colors_palette[i % len(colors_palette)],
                                  label=cluster_names[cid])
                  for i, cid in enumerate(cluster_ids)]

plt.legend(handles=legend_patches, loc='upper left', fontsize=10,
           framealpha=0.8, facecolor='#1a1a2e')
plt.title('Wykryte społeczności gier Steam\n(Algorytm Leiden, metryka Jaccard)',
          fontsize=18, fontweight='bold', color='white', pad=20)
plt.axis('off')
plt.tight_layout()

plt.savefig('poster_clusters.png', dpi=300, bbox_inches='tight',
            facecolor='#0a0a1a', edgecolor='none')
plt.savefig('poster_clusters.pdf', bbox_inches='tight',
            facecolor='#0a0a1a', edgecolor='none')

print("Zapisano: poster_clusters.png i poster_clusters.pdf")
driver.close()
