import os
from dotenv import load_dotenv
from falkordb import FalkorDB

# .env se credentials padho
load_dotenv()

db = FalkorDB(
    host=os.getenv("FALKORDB_HOST"),
    port=int(os.getenv("FALKORDB_PORT", "6379")),
    username=os.getenv("FALKORDB_USERNAME"),
    password=os.getenv("FALKORDB_PASSWORD"),
)

# ---------- SYNTHETIC (kalpanik) DATA ----------

# (name, kind, description)
COMPONENTS = [
    ("Login Service", "Service", "Handles user sign-in and authentication"),
    ("Auth Token Library", "Library", "Creates and validates login tokens"),
    ("User Database", "Database", "Stores user accounts"),
    ("Session Cache", "Database", "Keeps active login sessions in memory"),
    ("User Profile Service", "Service", "Stores and serves user profile data"),
    ("API Gateway", "Service", "Single entry point for all API requests"),
    ("Payment Service", "Service", "Processes payments for logged-in users"),
    ("Checkout Workflow", "Workflow", "Customer checkout from cart to payment"),
    ("Order Service", "Service", "Creates and tracks customer orders"),
    ("Notification Service", "Service", "Sends emails and push notifications"),
    ("Email Provider Adapter", "Library", "Connects to the email sending provider"),
    ("Mobile App Backend", "Service", "Backend used by the mobile app"),
    ("Admin Dashboard", "Service", "Internal tool for support staff"),
    ("Audit Log Service", "Service", "Records important security events"),
]

# (A, B) means: A DEPENDS_ON B  (A needs B to work)
DEPENDS_ON = [
    ("Login Service", "Auth Token Library"),
    ("Login Service", "User Database"),
    ("Login Service", "Session Cache"),
    ("User Profile Service", "Login Service"),
    ("API Gateway", "Login Service"),
    ("Payment Service", "Login Service"),
    ("Checkout Workflow", "Payment Service"),
    ("Checkout Workflow", "Order Service"),
    ("Order Service", "User Profile Service"),
    ("Mobile App Backend", "API Gateway"),
    ("Admin Dashboard", "Login Service"),
    ("Admin Dashboard", "Audit Log Service"),
    ("Notification Service", "User Profile Service"),
    ("Notification Service", "Email Provider Adapter"),
    ("Audit Log Service", "User Database"),
]

TEAMS = ["Identity Team", "Payments Team", "Platform Team", "Messaging Team", "Commerce Team"]

# (component, team)
OWNED_BY = [
    ("Login Service", "Identity Team"),
    ("Auth Token Library", "Identity Team"),
    ("User Database", "Identity Team"),
    ("Session Cache", "Identity Team"),
    ("User Profile Service", "Identity Team"),
    ("Payment Service", "Payments Team"),
    ("Checkout Workflow", "Payments Team"),
    ("API Gateway", "Platform Team"),
    ("Mobile App Backend", "Platform Team"),
    ("Admin Dashboard", "Platform Team"),
    ("Audit Log Service", "Platform Team"),
    ("Notification Service", "Messaging Team"),
    ("Email Provider Adapter", "Messaging Team"),
    ("Order Service", "Commerce Team"),
]

# (component, test name, test type)
TESTS = [
    ("Login Service", "test_login_success", "integration"),
    ("Login Service", "test_login_wrong_password", "unit"),
    ("Auth Token Library", "test_token_expiry", "unit"),
    ("User Profile Service", "test_profile_load_after_login", "integration"),
    ("API Gateway", "test_gateway_auth_header", "integration"),
    ("Payment Service", "test_payment_requires_login", "integration"),
    ("Checkout Workflow", "test_checkout_end_to_end", "e2e"),
    ("Order Service", "test_order_history_for_user", "integration"),
    ("Notification Service", "test_welcome_email_sent", "integration"),
    ("Admin Dashboard", "test_admin_login_flow", "e2e"),
    ("Mobile App Backend", "test_mobile_session_refresh", "integration"),
]

# (incident id, title, severity, [affected components])  -- ALL SYNTHETIC
INCIDENTS = [
    ("INC-001", "Token expiry bug logged users out unexpectedly", "high",
     ["Login Service", "Auth Token Library", "Mobile App Backend"]),
    ("INC-002", "Payment retries failed after session timeout", "medium",
     ["Payment Service", "Session Cache"]),
    ("INC-003", "Welcome emails delayed after profile schema change", "low",
     ["Notification Service", "User Profile Service"]),
    ("INC-004", "Gateway rejected valid tokens after config change", "high",
     ["API Gateway"]),
    ("INC-005", "Admin login loop after password policy update", "medium",
     ["Admin Dashboard", "Login Service"]),
]

# ---------- GRAPH BANANA ----------

# Purana graph hata do (agar hai), taaki script dobara chala sakein
try:
    db.select_graph("ripplemind").delete()
except Exception:
    pass

graph = db.select_graph("ripplemind")

for name, kind, desc in COMPONENTS:
    graph.query(
        "CREATE (:Component {name: $name, kind: $kind, description: $desc})",
        params={"name": name, "kind": kind, "desc": desc},
    )

for team in TEAMS:
    graph.query("CREATE (:Team {name: $name})", params={"name": team})

for a, b in DEPENDS_ON:
    graph.query(
        "MATCH (a:Component {name: $a}), (b:Component {name: $b}) "
        "CREATE (a)-[:DEPENDS_ON]->(b)",
        params={"a": a, "b": b},
    )

for comp, team in OWNED_BY:
    graph.query(
        "MATCH (c:Component {name: $c}), (t:Team {name: $t}) "
        "CREATE (c)-[:OWNED_BY]->(t)",
        params={"c": comp, "t": team},
    )

for comp, test_name, test_type in TESTS:
    graph.query(
        "MATCH (c:Component {name: $c}) "
        "CREATE (c)-[:TESTED_BY]->(:Test {name: $tn, type: $tt})",
        params={"c": comp, "tn": test_name, "tt": test_type},
    )

for inc_id, title, severity, comps in INCIDENTS:
    graph.query(
        "CREATE (:Incident {id: $id, title: $title, severity: $sev, synthetic: true})",
        params={"id": inc_id, "title": title, "sev": severity},
    )
    for comp in comps:
        graph.query(
            "MATCH (c:Component {name: $c}), (i:Incident {id: $id}) "
            "CREATE (c)-[:AFFECTED_BY]->(i)",
            params={"c": comp, "id": inc_id},
        )

# ---------- CHECK: kitna data bana? ----------
print("Graph 'ripplemind' created. Counting what is inside:")
for label in ["Component", "Team", "Test", "Incident"]:
    r = graph.ro_query(f"MATCH (n:{label}) RETURN count(n)")
    print(f"  {label} nodes:", r.result_set[0][0])

r = graph.ro_query("MATCH ()-[r]->() RETURN type(r), count(r)")
for rel_type, count in r.result_set:
    print(f"  {rel_type} relationships:", count)