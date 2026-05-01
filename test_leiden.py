import os
import pandas as pd
from neo4j import GraphDatabase

URI = "neo4j://neo4j:7687"
driver = GraphDatabase.driver(URI, auth=("neo4j", "password"))

def run_query(q):
    with driver.session() as s:
        res = s.run(q)
        return pd.DataFrame([r.values() for r in res], columns=res.keys())

print("Testing Leiden with gamma=2.0...")
try:
    print(run_query("""
    CALL gds.beta.leiden.stream('games_MED', {relationshipWeightProperty: 'jaccard', gamma: 2.0}) YIELD nodeId, communityId
    WITH communityId, count(*) as size ORDER BY size DESC LIMIT 10 RETURN size
    """))
except Exception as e:
    print(e)

driver.close()
