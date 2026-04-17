

import matplotlib.lines as mlines
from dataScraping.dataScraper import DataScraper

import yaml
import requests
import networkx as nx
import matplotlib.pyplot as plt
from collections import deque


def visualize_test_data(seed_id, max_records=150):
    scraper = DataScraper(seed_id, is_test=True)
    G = nx.Graph()
    
    counter = 0
    for record in scraper.run():
        if counter >= max_records:
            break
            
        if record['type'] == 'friend':
            G.add_node(record['source'], node_type='user', color='blue')
            G.add_node(record['target'], node_type='user', color='blue')
            G.add_edge(record['source'], record['target'])
            
        elif record['type'] == 'game':
            game_node = f"App_{record['app_id']}"
            G.add_node(record['steam_id'], node_type='user', color='blue')
            G.add_node(game_node, node_type='game', color='green')
            G.add_edge(record['steam_id'], game_node, weight=record['playtime'])
            
        counter += 1

    colors = [data.get('color', 'gray') for node, data in G.nodes(data=True)]
    
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=0.15, iterations=20)
    
    nx.draw(G, pos, node_color=colors, with_labels=False, node_size=40, edge_color="gray", alpha=0.6)
    
    legend_elements = [
        mlines.Line2D([0], [0], marker='o', color='w', label='Gracze', markerfacecolor='blue', markersize=10),
        mlines.Line2D([0], [0], marker='o', color='w', label='Gry', markerfacecolor='green', markersize=10)
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.title(f"Testowy Graf Sieci (Węzły: {len(G.nodes)}, Krawędzie: {len(G.edges)})")
    plt.show()

if __name__ == "__main__":
    visualize_test_data("76561198154174120")