import os
from dotenv import load_dotenv
from falkordb import FalkorDB

# .env file se host, port, username, password padhta hai
load_dotenv()

host = os.getenv("FALKORDB_HOST")
port = int(os.getenv("FALKORDB_PORT", "6379"))
username = os.getenv("FALKORDB_USERNAME")
password = os.getenv("FALKORDB_PASSWORD")

if not host or not password:
    print("ERROR: .env file mein host ya password nahi mila.")
    raise SystemExit(1)

try:
    # Database se connect karo
    db = FalkorDB(host=host, port=port, username=username, password=password)

    # Ek chhota test graph banao
    graph = db.select_graph("connection_test")
    graph.query("CREATE (:Test {name: 'hello'})")

    # Wapas padh ke dekho
    result = graph.ro_query("MATCH (t:Test) RETURN t.name")
    print("Connected! Data from FalkorDB:", result.result_set)

    # Test graph delete kar do (safai)
    graph.delete()
    print("Test graph deleted. Everything works.")
except Exception as e:
    print("Connection FAILED:", e)