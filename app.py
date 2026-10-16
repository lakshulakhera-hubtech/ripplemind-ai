import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

st.set_page_config(page_title="RippleMind AI", page_icon="🌊", layout="wide")

GRAPH_NAME = "ripplemind"

# ---------------- CYPHER QUERIES ----------------
# 1) Saare components jo selected component par (seedha ya door se) depend karte hain
Q_DEPENDENTS = """
MATCH p = (a:Component)-[:DEPENDS_ON*1..5]->(c:Component {name: $name})
RETURN a.name, a.kind, length(p), [n IN nodes(p) | n.name]
ORDER BY length(p), a.name
"""

# 2) Components ke list ke liye (dropdown)
Q_COMPONENTS = "MATCH (c:Component) RETURN c.name ORDER BY c.name"

# 3) Owner teams
Q_OWNERS = """
MATCH (c:Component)-[:OWNED_BY]->(t:Team)
WHERE c.name IN $names
RETURN c.name, t.name
"""

# 4) Tests jo check karne chahiye
Q_TESTS = """
MATCH (c:Component)-[:TESTED_BY]->(t:Test)
WHERE c.name IN $names
RETURN c.name, t.name, t.type
"""

# 5) Related incidents (synthetic demo data)
Q_INCIDENTS = """
MATCH (c:Component)-[:AFFECTED_BY]->(i:Incident)
WHERE c.name IN $names
RETURN c.name, i.id, i.title, i.severity
ORDER BY i.id
"""


# ---------------- DATABASE CONNECTION ----------------
@st.cache_resource
def get_graph():
    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        username=os.getenv("FALKORDB_USERNAME"),
        password=os.getenv("FALKORDB_PASSWORD"),
    )
    return db.select_graph(GRAPH_NAME)


# ---------------- ANALYSIS ----------------
def analyze(graph, name, change_text):
    rows = graph.ro_query(Q_DEPENDENTS, params={"name": name}).result_set

    # Har component ka sabse chhota path rakho; kitne paths hain woh bhi gino
    found = {}
    for comp, kind, hops, path in rows:
        if comp not in found:
            found[comp] = {
                "component": comp,
                "kind": kind,
                "hops": hops,
                "path": path,
                "path_count": 1,
            }
        else:
            found[comp]["path_count"] += 1
    affected = list(found.values())

    names = [name] + [a["component"] for a in affected]

    owners = {
        c: t for c, t in graph.ro_query(Q_OWNERS, params={"names": names}).result_set
    }
    tests = graph.ro_query(Q_TESTS, params={"names": names}).result_set
    incidents = graph.ro_query(Q_INCIDENTS, params={"names": names}).result_set

    incident_comps = {row[0] for row in incidents}

    # INFERRED risk: yeh sirf simple rules hain, graph ka verified fact nahi
    risks = []
    for a in affected:
        score = 0
        reasons = []
        if a["hops"] == 1:
            score += 2
            reasons.append("depends directly on the changed component")
        elif a["hops"] == 2:
            score += 1
            reasons.append("depends on it through 1 other component")
        else:
            reasons.append(f"depends on it through {a['hops'] - 1} other components")
        if a["component"] in incident_comps:
            score += 1
            reasons.append("has a linked (synthetic) past incident")
        if a["path_count"] > 1:
            score += 1
            reasons.append(f"reachable through {a['path_count']} different paths")
        level = "High" if score >= 3 else "Medium" if score >= 2 else "Low"
        risks.append({"component": a["component"], "risk": level, "why": "; ".join(reasons)})

    return {
        "selected": name,
        "change": change_text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "affected": affected,
        "owners": owners,
        "tests": tests,
        "incidents": incidents,
        "risks": risks,
    }


# ---------------- HELPERS FOR DISPLAY ----------------
def path_text(path):
    return " → ".join(path)


def hop_label(hops):
    return "Direct" if hops == 1 else f"Indirect ({hops} steps)"


def build_dot(selected, affected):
    lines = [
        "digraph G {",
        "rankdir=LR;",
        'node [shape=box, style="filled,rounded", fontname="Helvetica"];',
        f'"{selected}" [fillcolor="#ff8a80"];',
    ]
    edges = set()
    for a in affected:
        color = "#ffcc80" if a["hops"] == 1 else "#fff59d"
        lines.append(f'"{a["component"]}" [fillcolor="{color}"];')
        p = a["path"]
        for i in range(len(p) - 1):
            edges.add((p[i], p[i + 1]))
    for s, t in sorted(edges):
        lines.append(f'"{s}" -> "{t}";')
    lines.append("}")
    return "\n".join(lines)


def build_report(r):
    out = []
    out.append("# RippleMind AI - Impact Report")
    out.append(f"Generated: {r['time']}")
    out.append("")
    out.append(f"**Component to change:** {r['selected']}")
    out.append(f"**Proposed change:** {r['change']}")
    out.append("")
    out.append("> All data comes from a synthetic demo graph in FalkorDB. Incidents are fictional.")
    out.append("")
    out.append("## Verified graph facts: affected components")
    if r["affected"]:
        for a in r["affected"]:
            owner = r["owners"].get(a["component"], "unknown")
            out.append(
                f"- {a['component']} ({a['kind']}), {hop_label(a['hops'])}, owner: {owner}. "
                f"Path: {path_text(a['path'])}"
            )
    else:
        out.append("- No components depend on this component in the graph.")
    out.append("")
    out.append("## Verified graph facts: tests to check")
    for comp, tname, ttype in r["tests"]:
        out.append(f"- {tname} ({ttype}) covers {comp}")
    out.append("")
    out.append("## Verified graph facts: related synthetic incidents")
    for comp, iid, title, sev in r["incidents"]:
        out.append(f"- {iid} [{sev}] {title} (linked to {comp})")
    out.append("")
    out.append("## Inferred risks (rule-based, NOT verified facts)")
    for k in r["risks"]:
        out.append(f"- {k['component']}: {k['risk']} - {k['why']}")
    out.append("")
    out.append(
        "Note: the proposed change text is only recorded in this report. "
        "The graph analysis does not interpret it."
    )
    return "\n".join(out)


def show_result(r):
    affected = r["affected"]
    direct = [a for a in affected if a["hops"] == 1]
    indirect = [a for a in affected if a["hops"] > 1]
    n_incidents = len({row[1] for row in r["incidents"]})

    st.divider()
    st.header(f"Impact of changing: {r['selected']}")
    st.write(f"**Proposed change:** {r['change']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Direct dependents", len(direct))
    c2.metric("Indirect dependents", len(indirect))
    c3.metric("Tests to check", len(r["tests"]))
    c4.metric("Related incidents", n_incidents)

    # ---------- VERIFIED ----------
    st.subheader("✅ Verified from the graph")
    if not affected:
        st.success(
            "No components depend on this component in the graph. "
            "This does not prove the change is safe. It only means no dependents are recorded."
        )
    else:
        st.markdown("**Affected components** (arrow `A → B` means A depends on B)")
        st.dataframe(
            [
                {
                    "Component": a["component"],
                    "Type": a["kind"],
                    "Distance": hop_label(a["hops"]),
                    "Owner team": r["owners"].get(a["component"], "unknown"),
                    "Supporting path": path_text(a["path"]),
                }
                for a in affected
            ],
            hide_index=True,
        )

        with st.expander("Why is each component affected? (plain English)"):
            for a in affected:
                p = a["path"]
                steps = [f"{p[i]} depends on {p[i + 1]}" for i in range(len(p) - 1)]
                st.write(f"**{a['component']}**: " + "; ".join(steps) + ".")

        st.markdown("**Graph picture** (red = changed, orange = direct, yellow = indirect)")
        st.graphviz_chart(build_dot(r["selected"], affected))

    st.markdown("**Tests to check**")
    if r["tests"]:
        order = {r["selected"]: 0}
        for a in affected:
            order[a["component"]] = a["hops"]
        tests_sorted = sorted(r["tests"], key=lambda x: order.get(x[0], 99))
        st.dataframe(
            [
                {
                    "Test": t[1],
                    "Type": t[2],
                    "Covers": t[0],
                    "Why": "Changed component"
                    if t[0] == r["selected"]
                    else hop_label(order.get(t[0], 99)) + " dependent",
                }
                for t in tests_sorted
            ],
            hide_index=True,
        )
    else:
        st.info("No tests are recorded for these components in the graph.")

    st.markdown("**Related incidents** (⚠️ SYNTHETIC demo data, not real incidents)")
    if r["incidents"]:
        st.dataframe(
            [
                {"Incident": i[1], "Severity": i[3], "Title": i[2], "Linked to": i[0]}
                for i in r["incidents"]
            ],
            hide_index=True,
        )
    else:
        st.info("No incidents are linked to these components in the graph.")

    # ---------- INFERRED ----------
    st.subheader("⚠️ Inferred risks (rule-based guesses, not verified facts)")
    st.caption(
        "Rules: closer dependents score higher, a linked past incident adds a point, "
        "and several paths add a point. This is a simple heuristic, not a prediction."
    )
    if r["risks"]:
        st.dataframe(
            [
                {"Component": k["component"], "Risk": k["risk"], "Reason": k["why"]}
                for k in r["risks"]
            ],
            hide_index=True,
        )
    else:
        st.info("Nothing to score.")

    st.caption(
        "Your change description is saved in the report but is not interpreted by the analysis."
    )

    with st.expander("Cypher queries used (evidence)"):
        st.code(Q_DEPENDENTS.strip(), language="cypher")
        st.code(Q_OWNERS.strip(), language="cypher")
        st.code(Q_TESTS.strip(), language="cypher")
        st.code(Q_INCIDENTS.strip(), language="cypher")

    st.download_button(
        "⬇️ Download report (.md)",
        data=build_report(r),
        file_name="ripplemind_report.md",
        mime="text/markdown",
    )


# ---------------- PAGE ----------------
st.title("🌊 RippleMind AI")
st.caption("Explainable software change-impact analysis, powered by a FalkorDB graph (synthetic demo data)")

try:
    graph = get_graph()
    component_names = [row[0] for row in graph.ro_query(Q_COMPONENTS).result_set]
except Exception as e:
    st.error(
        "Could not read from FalkorDB. Check your .env file, check that the instance is Running, "
        "and run `python seed_graph.py` if you have not yet."
    )
    st.caption(f"Technical detail: {e}")
    st.stop()

if not component_names:
    st.warning("The graph is empty. Run `python seed_graph.py` in the terminal first.")
    st.stop()

st.success("✅ Connected to FalkorDB")

selected = st.selectbox("Which component do you want to change?", component_names)
change = st.text_area(
    "Describe the change you want to make",
    placeholder="Example: I want to change the login authentication process.",
)

if st.button("Analyze impact"):
    if not change.strip():
        st.warning("Please describe the change first.")
    else:
        try:
            st.session_state["result"] = analyze(graph, selected, change.strip())
        except Exception as e:
            st.session_state.pop("result", None)
            st.error("The analysis query failed.")
            st.caption(f"Technical detail: {e}")

if "result" in st.session_state:
    show_result(st.session_state["result"])