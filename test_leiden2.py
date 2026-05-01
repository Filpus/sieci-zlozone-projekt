import os
import pandas as pd
from neo4j import GraphDatabase

URI = "neo4j://neo4j:7687"
driver = GraphDatabase.driver(URI, auth=("neo4j", "password"))

def run_query(q):
    with driver.session() as s:
        res = s.run(q)
        return pd.DataFrame([r.values() for r in res], columns=res.keys())

print("Creating undirected projection...")
try: driver.session().run("CALL gds.graph.drop('games_MED_undirected', false)")
except: pass

run_query("""
CALL gds.graph.project(
  'games_MED_undirected',
  'Game',
  {SIMILAR_MED: {orientation: 'UNDIRECTED', properties: 'jaccard'}}
)
""")

print("Testing Leiden with gamma=1.0...")
print(run_query("""
CALL gds.beta.leiden.stream('games_MED_undirected', {relationshipWeightProperty: 'jaccard', gamma: 1.0}) YIELD nodeId, communityId
WITH communityId, count(*) as size ORDER BY size DESC LIMIT 10 RETURN size
"""))

print("Testing Leiden with gamma=2.0 (more granular)...")
print(run_query("""
CALL gds.beta.leiden.stream('games_MED_undirected', {relationshipWeightProperty: 'jaccard', gamma: 2.0}) YIELD nodeId, communityId
WITH communityId, count(*) as size ORDER BY size DESC LIMIT 10 RETURN size
"""))

driver.close()
