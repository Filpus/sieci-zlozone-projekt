import os
import pandas as pd
from neo4j import GraphDatabase

URI = "neo4j://neo4j:7687"
driver = GraphDatabase.driver(URI, auth=("neo4j", "password"))

def run_query(q):
    with driver.session() as s:
        res = s.run(q)
        return pd.DataFrame([r.values() for r in res], columns=res.keys())

# Test resolution = 1.0 (default)
print("Default (Jaccard):")
print(run_query("""
CALL gds.louvain.stream('games_MED', {relationshipWeightProperty: 'jaccard'}) YIELD nodeId, communityId
WITH communityId, count(*) as size ORDER BY size DESC LIMIT 5 RETURN size
"""))

# Test resolution = 5.0
print("\nResolution = 5.0:")
print(run_query("""
CALL gds.louvain.stream('games_MED', {relationshipWeightProperty: 'jaccard', resolution: 5.0}) YIELD nodeId, communityId
WITH communityId, count(*) as size ORDER BY size DESC LIMIT 5 RETURN size
"""))

driver.close()
