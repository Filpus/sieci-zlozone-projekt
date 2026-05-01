import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("# Projekt Sieci Złożone: Analiza Społeczności na Różnych Poziomach Gęstości\n\nTen notatnik analizuje i porównuje wyniki dla całej sieci (SIMILAR) oraz trzech różnych progów filtrowania (LOW, MED, HIGH)."),
    
    nbf.v4.new_code_cell("""\
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from neo4j import GraphDatabase
import warnings
warnings.filterwarnings('ignore')

# Ustawienia wykresów
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")

# Konfiguracja połączenia
URI = os.environ.get("NEO4J_URI", "neo4j://neo4j:7687")
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def run_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters)
        return pd.DataFrame([r.values() for r in result], columns=result.keys())"""),

    nbf.v4.new_markdown_cell("## 1. Porównanie Podstawowych Statystyk Wszystkich Typów Relacji\nSprawdzamy statystyki dla pełnego grafu oraz przefiltrowanych wersji."),
    
    nbf.v4.new_code_cell("""\
rel_types = ['SIMILAR', 'SIMILAR_LOW', 'SIMILAR_MED', 'SIMILAR_HIGH']
stats = []

for rel in rel_types:
    query = f\"\"\"
    MATCH (n:Game)
    WITH count(n) AS total_nodes
    OPTIONAL MATCH ()-[r:{rel}]->()
    WITH total_nodes, count(r) AS num_edges
    MATCH (n:Game)
    WHERE apoc.node.degree(n, '{rel}') > 0
    WITH total_nodes, num_edges, count(n) AS active_nodes, max(apoc.node.degree(n, '{rel}')) AS max_deg, avg(apoc.node.degree(n, '{rel}')) AS avg_deg
    RETURN '{rel}' AS rel_type, 
           total_nodes, 
           active_nodes, 
           total_nodes - active_nodes AS isolated_nodes,
           num_edges, 
           max_deg, 
           avg_deg, 
           CASE WHEN active_nodes > 1 THEN (num_edges * 2.0) / (active_nodes * (active_nodes - 1)) ELSE 0 END AS density_active
    \"\"\"
    stats.append(run_query(query))

df_stats = pd.concat(stats).reset_index(drop=True)
display(df_stats)
"""),

    nbf.v4.new_markdown_cell("## 2. Projekcja GDS i Algorytm Louvain dla poszczególnych progów\nOdpalamy algorytm detekcji społeczności dla 3 przefiltrowanych sieci, zapisując wyniki do oddzielnych właściwości (community_id_low, med, high)."),

    nbf.v4.new_code_cell("""\
# Oczyszczanie ewentualnych starych projekcji
for suffix in ['LOW', 'MED', 'HIGH']:
    try:
        with driver.session() as session:
            session.run(f"CALL gds.graph.drop('games_{suffix}', false)")
    except: pass

louvain_results = []

for suffix in ['LOW', 'MED', 'HIGH']:
    rel_type = f"SIMILAR_{suffix}"
    prop_name = f"community_id_{suffix.lower()}"
    graph_name = f"games_{suffix}"
    
    print(f"Przetwarzanie {rel_type}...")
    
    # 1. Tworzenie projekcji natywnej (Nieskierowanej dla algorytmu Leiden)
    query_project = f\"\"\"
    CALL gds.graph.project(
      '{graph_name}',
      'Game',
      {{ {rel_type}: {{ orientation: 'UNDIRECTED', properties: 'jaccard' }} }}
    ) YIELD nodeCount, relationshipCount
    \"\"\"
    run_query(query_project)
    
    # 2. Uruchamianie algorytmu Leiden (nowoczesnego następcy Louvain) z parametrem rozdzielczości
    query_louvain = f\"\"\"
    CALL gds.leiden.write('{graph_name}', {{
      relationshipWeightProperty: 'jaccard',
      writeProperty: '{prop_name}',
      gamma: 2.0
    }})
    YIELD communityCount, modularity
    RETURN '{rel_type}' AS rel_type, communityCount, modularity
    \"\"\"
    louvain_results.append(run_query(query_louvain))

df_louvain = pd.concat(louvain_results).reset_index(drop=True)
display(df_louvain)
print("Społeczności zostały zapisane w Neo4j!")
"""),

    nbf.v4.new_markdown_cell("## 3. Rozkład Wielkości Społeczności (Dla wszystkich progów)"),

    nbf.v4.new_code_cell("""\
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for i, suffix in enumerate(['low', 'med', 'high']):
    prop = f"community_id_{suffix}"
    query = f\"\"\"
    MATCH (g:Game)
    WHERE g.{prop} IS NOT NULL AND apoc.node.degree(g, 'SIMILAR_' + toUpper('{suffix}')) > 0
    RETURN g.{prop} AS community, count(g) AS size
    ORDER BY size DESC
    LIMIT 10
    \"\"\"
    df = run_query(query)
    sns.barplot(data=df, x='community', y='size', order=df['community'], palette='viridis', ax=axes[i])
    axes[i].set_title(f'Top 10 (Progi: {suffix.upper()})')
    axes[i].set_xlabel('ID Społeczności')
    axes[i].set_ylabel('Liczba Gier')

plt.tight_layout()
plt.show()
"""),

    nbf.v4.new_markdown_cell("## 3b. Porównanie różnych metryk podobieństwa\nSprawdzamy, jak zmiana metryki (Jaccard, Cosine, Overlap, Resource Allocation) na tych samych krawędziach (SIMILAR_MED) wpływa na algorytm Leiden."),

    nbf.v4.new_code_cell("""\
metrics = ['jaccard', 'cosine', 'overlap', 'resource_allocation']

try: driver.session().run("CALL gds.graph.drop('games_metrics', false)")
except: pass

print("Tworzenie projekcji z wieloma metrykami...")
query_metrics_proj = \"\"\"
CALL gds.graph.project(
  'games_metrics',
  'Game',
  { SIMILAR_MED: { orientation: 'UNDIRECTED', properties: ['jaccard', 'cosine', 'overlap', 'resource_allocation'] } }
) YIELD nodeCount
\"\"\"
run_query(query_metrics_proj)

metrics_results = []
for metric in metrics:
    print(f"Uruchamianie Leiden dla metryki: {metric}")
    q = f\"\"\"
    CALL gds.leiden.write('games_metrics', {
      relationshipWeightProperty: '{metric}',
      writeProperty: 'community_' + '{metric}',
      gamma: 2.0
    })
    YIELD communityCount, modularity
    RETURN '{metric}' AS metric, communityCount, modularity
    \"\"\"
    metrics_results.append(run_query(q))

df_metrics = pd.concat(metrics_results).reset_index(drop=True)
display(df_metrics)
"""),

    nbf.v4.new_code_cell("""\
fig, axes = plt.subplots(1, 4, figsize=(24, 5))

for i, metric in enumerate(metrics):
    prop = f"community_{metric}"
    query = f\"\"\"
    MATCH (g:Game)
    WHERE g.{prop} IS NOT NULL AND apoc.node.degree(g, 'SIMILAR_MED') > 0
    RETURN g.{prop} AS community, count(g) AS size
    ORDER BY size DESC
    LIMIT 10
    \"\"\"
    df = run_query(query)
    sns.barplot(data=df, x='community', y='size', order=df['community'], palette='magma', ax=axes[i])
    axes[i].set_title(f'Top 10 ({metric})')
    axes[i].set_xlabel('ID Społeczności')
    axes[i].set_ylabel('Liczba Gier')

plt.tight_layout()
plt.show()
"""),

    nbf.v4.new_markdown_cell("## 4. Dominujące Gatunki w Społecznościach (Skupmy się na średnim progu - MED)"),

    nbf.v4.new_code_cell("""\
query_genres = \"\"\"
MATCH (g:Game)
WHERE g.community_id_med IS NOT NULL AND apoc.node.degree(g, 'SIMILAR_MED') > 0
WITH g.community_id_med AS community, count(g) AS size
ORDER BY size DESC LIMIT 6

MATCH (g:Game)
WHERE g.community_id_med = community AND g.genres IS NOT NULL AND g.genres <> ''
UNWIND split(g.genres, '|') AS genre
WITH community, genre, count(*) AS count
ORDER BY count DESC
WITH community, collect({genre: genre, count: count})[0..4] AS top_genres
UNWIND top_genres AS tg
RETURN community, tg.genre AS genre, tg.count AS count
\"\"\"
df_genres = run_query(query_genres)

plt.figure(figsize=(14, 8))
sns.barplot(data=df_genres, x='community', y='count', hue='genre', palette='tab10')
plt.title('Dominujące oficjalne gatunki wewnątrz poszczególnych społeczności (SIMILAR_MED)')
plt.xlabel('ID Społeczności')
plt.ylabel('Liczba wystąpień gatunku')
plt.legend(title='Gatunek', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()
"""),

    nbf.v4.new_markdown_cell("## 5. Homofilia Gatunkowa (Z wykorzystaniem krawędzi HIGH)\nUżywając najsilniejszych powiązań (SIMILAR_HIGH) badamy, które gatunki łączą się w hermetyczne grupy."),
    
    nbf.v4.new_code_cell("""\
query_homophily = \"\"\"
MATCH (n:Game)-[r:SIMILAR_HIGH]-(m:Game)
WHERE n.genres IS NOT NULL AND m.genres IS NOT NULL
UNWIND split(n.genres, '|') AS genre_n
UNWIND split(m.genres, '|') AS genre_m
WITH genre_n, genre_m, count(r) AS connections
WHERE connections > 100
RETURN genre_n AS Zrodlo, genre_m AS Cel, connections AS Sila_Polaczenia
ORDER BY Sila_Polaczenia DESC
LIMIT 400
\"\"\"
df_homophily = run_query(query_homophily)
pivot = df_homophily.pivot(index='Zrodlo', columns='Cel', values='Sila_Polaczenia').fillna(0)

plt.figure(figsize=(12, 10))
sns.heatmap(pivot, cmap='YlOrRd', annot=True, fmt=".0f", linewidths=.5)
plt.title('Heatmapa Połączeń Międzygatunkowych (SIMILAR_HIGH - Graf Nieskierowany)')
plt.show()
""")
]

with open("analysis_communities.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Notatnik rozszerzony o wszystkie typy krawedzi zostal wygenerowany.")
