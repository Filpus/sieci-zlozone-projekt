import os
import pandas as pd
from neo4j import GraphDatabase

URI = "neo4j://neo4j:7687"
driver = GraphDatabase.driver(URI, auth=("neo4j", "password"))

def run_query(q):
    with driver.session() as s:
        res = s.run(q)
        return pd.DataFrame([r.values() for r in res], columns=res.keys())

print("Creating projection with resource_allocation...")
try:
    driver.session().run("CALL gds.graph.drop('games_MED_ra', false)")
except: pass

run_query("""
CALL gds.graph.project(
  'games_MED_ra',
  'Game',
  'SIMILAR_MED',
  {relationshipProperties: 'resource_allocation'}
) YIELD nodeCount
""")

print("Testing Louvain with resource_allocation...")
print(run_query("""
CALL gds.louvain.stream('games_MED_ra', {relationshipWeightProperty: 'resource_allocation'}) YIELD nodeId, communityId
WITH communityId, count(*) as size ORDER BY size DESC LIMIT 10 RETURN size
"""))

driver.close()
