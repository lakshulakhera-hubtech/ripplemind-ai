# 🌊 RippleMind AI

Explainable software change-impact analysis powered by a **FalkorDB** graph.

Built for **Graph Hacks 2026 (WeMakeDevs x FalkorDB), Track 01: Agents That Act on Connected Data**.

## Problem
When a developer changes one software component, other connected components, services, workflows and tests can break. RippleMind AI queries a graph of those connections and shows what a change may affect, and why.

## What it does
Pick a component (for example "Login Service"), describe the change, and the app shows:
- Direct and indirect dependents, found with Cypher variable-length path queries
- The exact supporting path for each finding (A → B → C)
- Owner team for each affected component
- Tests to check, ordered by closeness to the change
- Related incidents (**synthetic demo data only, not real incidents**)
- A graph picture of the connections
- A downloadable Markdown report

**Verified vs inferred:** results under "Verified from the graph" come straight from FalkorDB query results. The "Inferred risks" table is a simple rule-based score (distance, linked incident, number of paths). It is a heuristic, not a prediction.

## FalkorDB is the core
All analysis runs as Cypher queries against FalkorDB. Without the graph, the app cannot produce results.

## Graph data model
Nodes: `Component` (name, kind, description), `Team`, `Test`, `Incident` (synthetic: true)

Relationships:
- `(A:Component)-[:DEPENDS_ON]->(B:Component)` means A depends on B
- `(Component)-[:OWNED_BY]->(Team)`
- `(Component)-[:TESTED_BY]->(Test)`
- `(Component)-[:AFFECTED_BY]->(Incident)`

The demo graph has 14 components, 5 teams, 11 tests, 5 incidents (all fictional), created by `seed_graph.py`.

## Example Cypher (from app.py)
```cypher
MATCH p = (a:Component)-[:DEPENDS_ON*1..5]->(c:Component {name: $name})
RETURN a.name, a.kind, length(p), [n IN nodes(p) | n.name]
ORDER BY length(p), a.name
```

## Architecture
Streamlit UI (`app.py`) → Python (`falkordb` client) → FalkorDB Cloud graph `ripplemind` → results shown as tables, graph picture and report.

## Setup
1. Install Python 3.11 or newer.
2. Create a free instance on FalkorDB Cloud (https://app.falkordb.cloud).
3. Clone and install:
```
git clone https://github.com/lakshulakhera-hubtech/ripplemind-ai.git
cd ripplemind-ai
python -m pip install -r requirements.txt
```
4. Create a file named `.env` in the project folder (never commit it):
```
FALKORDB_HOST=your-host
FALKORDB_PORT=your-port
FALKORDB_USERNAME=falkordb
FALKORDB_PASSWORD=your-password
```
5. Load the synthetic demo data, then run the app:
```
python seed_graph.py
python -m streamlit run app.py
```

## Testing (manual, run on 2026-10-16)
Expected numbers were calculated by hand from the seed data, then compared with the app output. All four matched.

| Component changed | Direct | Indirect | Tests | Incidents |
|---|---|---|---|---|
| Login Service | 4 | 4 | 10 | 5 |
| Payment Service | 1 | 0 | 2 | 1 |
| Checkout Workflow (no dependents) | 0 | 0 | 1 | 0 |
| User Database (multi-path) | 2 | 8 | 10 | 5 |

`test_connection.py` also confirmed a working connection to FalkorDB Cloud.

Not tested: database connection failure handling and graph changes after seeding. There are no automated unit tests.

## Limitations
- Demo data is fictional. Incidents are not real.
- The text of the proposed change is saved in the report but is not interpreted by the analysis.
- The risk score is a simple heuristic.
- No live deployment. The app runs locally.

## AI-tool disclosure
This project was built with help from Claude (Anthropic), which generated most of the code (app.py, seed_graph.py, test_connection.py) and the README draft, and guided the setup step by step. I set up the FalkorDB Cloud instance, configured the credentials in a local .env file (not uploaded), ran the seed script and the app, tested several components in the app, and compared the results with expected numbers that were calculated from the seed data with Claude's help. I did not write the code from scratch.
