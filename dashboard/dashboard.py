
import time, requests, streamlit as st, pandas as pd, altair as alt

st.set_page_config(page_title="RecSys A/B Dashboard", layout="wide")

st.markdown("""
<style>
/* ── base ── */
[data-testid="stAppViewContainer"] { background-color: #f5f0e8; }
[data-testid="stHeader"]           { background-color: #f5f0e8; }
[data-testid="stSidebar"]          { background-color: #ede8dc; }
[data-testid="stSidebar"] > div    { background-color: #ede8dc; }

/* ── global text → black ── */
html, body, [class*="css"], [data-testid="stMarkdownContainer"],
.stMarkdown, .stText, p, span, div, label, caption,
[data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"] {
    color: #000000 !important;
}

/* ── headings ── */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    color: #000000 !important;
    font-weight: 700;
}

/* ── sidebar text ── */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] .stCaption {
    color: #000000 !important;
}

/* ── metric cards ── */
[data-testid="metric-container"] {
    background: #faf7f2;
    border: 1px solid #c8c0b0;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="metric-container"] label,
[data-testid="metric-container"] [data-testid="stMetricValue"],
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: #000000 !important;
}
[data-testid="stMetricValue"] {
    font-weight: 700;
    font-size: 1.5rem !important;
}

/* ── tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid #c8c0b0;
}
[data-testid="stTabs"] [role="tab"] {
    color: #000000 !important;
    font-weight: 500;
    font-size: 0.95rem;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #000000 !important;
    font-weight: 700;
    border-bottom: 3px solid #8b6f47;
}

/* ── buttons ── */
[data-testid="stButton"] > button[kind="primary"] {
    background-color: #8b6f47;
    color: #ffffff !important;
    border: none;
    border-radius: 6px;
    font-weight: 600;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #7a5f3a;
    color: #ffffff !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    border: 1.5px solid #8b6f47;
    color: #000000 !important;
    border-radius: 6px;
    background: transparent;
    font-weight: 500;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background-color: #ede8dc;
    color: #000000 !important;
}

/* ── inputs & selects ── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"]   input,
[data-testid="stSelectbox"]   div {
    color: #000000 !important;
    background-color: #faf7f2;
    border-color: #c8c0b0;
}

/* ── expanders ── */
[data-testid="stExpander"] {
    background: #faf7f2;
    border: 1px solid #c8c0b0;
    border-radius: 6px;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] p {
    color: #000000 !important;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td {
    color: #000000 !important;
}

/* ── alerts ── */
[data-testid="stAlert"] p,
[data-testid="stAlert"] span {
    color: #000000 !important;
}

/* ── divider ── */
hr { border-color: #c8c0b0; }

/* ── variant badges ── */
.variant-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.variant-control   { background: #2d2a26; color: #ffffff; }
.variant-treatment { background: #1a2e1f; color: #ffffff; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("A/B Dashboard")
    st.caption("recsys-ab-testing · exp_001")
    st.divider()
    api_base = st.text_input("API base URL", value="__API_URL__")
    alpha = st.slider("Significance level (a)", 0.01, 0.10, 0.05, 0.01)
    st.divider()
    auto_refresh = st.checkbox("Auto-refresh stats", value=False)
    refresh_sec  = st.number_input("Refresh interval (s)", 5, 60, 10, step=5, disabled=not auto_refresh)
    if auto_refresh:
        time.sleep(refresh_sec); st.rerun()
    st.divider()
    st.caption("ALS (control) vs Content-Based (treatment) · 50/50 split")

def get(path, **params):
    try:
        r = requests.get(f"{api_base}{path}", params=params, timeout=5)
        r.raise_for_status(); return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API."
    except Exception as e:
        return None, str(e)

def post(path, payload):
    try:
        r = requests.post(f"{api_base}{path}", json=payload, timeout=5)
        r.raise_for_status(); return r.json(), None
    except Exception as e:
        return None, str(e)

def variant_badge(v):
    cls = "variant-control" if v == "control" else "variant-treatment"
    return f'<span class="variant-badge {cls}">{v}</span>'

health, err = get("/health")
if err:
    st.error(f"API Offline — {err}"); st.stop()

tab_stats, tab_sig, tab_recs, tab_variant = st.tabs([
    "Live Stats", "Significance", "Recommendations", "Variant Lookup"])

with tab_stats:
    st.header("Live CTR per Variant")
    st.caption("Pulled from GET /experiment/stats")
    stats, err = get("/experiment/stats")
    if err:
        st.error(err)
    elif stats:
        ctrl = stats.get("control", {})
        trt  = stats.get("treatment", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Control impressions", f"{ctrl.get('impressions', 0):,}")
        c2.metric("Control CTR", f"{ctrl.get('ctr', 0):.2%}")
        c3.metric("Treatment impressions", f"{trt.get('impressions', 0):,}")
        delta = trt.get('ctr', 0) - ctrl.get('ctr', 0)
        c4.metric("Treatment CTR", f"{trt.get('ctr', 0):.2%}", delta=f"{delta:+.2%}")
        st.divider()
        df = pd.DataFrame([
            {"Variant": "control",   "Impressions": ctrl.get('impressions', 0), "Clicks": ctrl.get('clicks', 0), "CTR": ctrl.get('ctr', 0)},
            {"Variant": "treatment", "Impressions": trt.get('impressions', 0),  "Clicks": trt.get('clicks', 0),  "CTR": trt.get('ctr', 0)},
        ])
        col1, col2 = st.columns(2)
        with col1:
            melted = df.melt(id_vars=["Variant"], value_vars=["Impressions", "Clicks"],
                             var_name="Event", value_name="Count")
            st.altair_chart(
                alt.Chart(melted)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Variant:N", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Count:Q"),
                    color=alt.Color("Event:N", scale=alt.Scale(range=["#8b6f47", "#c4a882"])),
                    xOffset="Event:N",
                    tooltip=["Variant:N", "Event:N", "Count:Q"],
                )
                .properties(title="Event Volume", height=280)
                .configure_view(strokeWidth=0)
                .configure_axis(grid=False, labelColor="#000000", titleColor="#000000")
                .configure_title(color="#000000"),
                use_container_width=True)
        with col2:
            st.altair_chart(
                alt.Chart(df)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Variant:N", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("CTR:Q", axis=alt.Axis(format=".1%")),
                    color=alt.Color("Variant:N", scale=alt.Scale(
                        domain=["control", "treatment"],
                        range=["#8b6f47", "#5aab6d"]), legend=None),
                    tooltip=["Variant:N", alt.Tooltip("CTR:Q", format=".3%")])
                .properties(title="CTR", height=280)
                .configure_view(strokeWidth=0)
                .configure_axis(grid=False, labelColor="#000000", titleColor="#000000")
                .configure_title(color="#000000"),
                use_container_width=True)
        with st.expander("Raw JSON"):
            st.json(stats)

with tab_sig:
    st.header("Statistical Significance")
    st.caption(f"Two-proportion z-test · alpha = {alpha} · GET /experiment/significance")
    if st.button("Run significance test", type="primary"):
        result, err = get("/experiment/significance", alpha=alpha)
        if err:
            st.error(err)
        elif result:
            sig    = result.get("is_significant", False)
            winner = result.get("winner") or "undecided"
            if sig:
                st.success(f"Statistically significant (p = {result['p_value']:.4f} < alpha {alpha}) — winner: {winner}")
            else:
                st.warning(f"Not yet significant (p = {result['p_value']:.4f} >= alpha {alpha}) — keep collecting data.")
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Control CTR",   f"{result['control_ctr']:.4%}")
            c1.metric("Treatment CTR", f"{result['treatment_ctr']:.4%}", delta=f"{result['absolute_lift']:+.4%}")
            c2.metric("Relative lift", f"{result['relative_lift_pct']:+.2f}%")
            c2.metric("Z-statistic",   f"{result['z_statistic']:.4f}")
            c3.metric("p-value",       f"{result['p_value']:.6f}")
            c3.metric("95% CI",        f"[{result['ci_lower']:+.4%}, {result['ci_upper']:+.4%}]")
            st.divider()
            lift_df = pd.DataFrame([{
                "label":    "Absolute lift",
                "estimate": result["absolute_lift"],
                "ci_lower": result["ci_lower"],
                "ci_upper": result["ci_upper"],
            }])
            st.altair_chart(
                alt.layer(
                    alt.Chart(lift_df).mark_rule(strokeWidth=2, color="#8b6f47")
                        .encode(x="ci_lower:Q", x2="ci_upper:Q", y=alt.Y("label:N", title="")),
                    alt.Chart(lift_df).mark_point(size=120, filled=True)
                        .encode(
                            x=alt.X("estimate:Q", axis=alt.Axis(format=".2%", title="Absolute lift")),
                            y=alt.Y("label:N", title=""),
                            color=alt.condition(alt.datum.estimate > 0,
                                                alt.value("#5aab6d"), alt.value("#c0614a"))),
                    alt.Chart(pd.DataFrame([{"x": 0}]))
                        .mark_rule(strokeDash=[4, 4], color="#9e9488", strokeWidth=1)
                        .encode(x="x:Q"),
                )
                .properties(title="95% CI on Lift", height=120)
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor="#000000", titleColor="#000000")
                .configure_title(color="#000000"),
                use_container_width=True)
            with st.expander("Full JSON"):
                st.json(result)
    else:
        st.info("Click Run significance test to fetch the latest result.")

with tab_recs:
    st.header("Recommendations")
    st.caption("GET /recommend — variant assigned and impression logged automatically.")
    col_uid, col_n, col_btn = st.columns([2, 1, 1])
    user_id = col_uid.number_input("User ID", min_value=0, max_value=99999, value=42, step=1)
    n_recs  = col_n.number_input("Top-N", min_value=1, max_value=50, value=10, step=1)
    col_btn.markdown("<br>", unsafe_allow_html=True)
    fetch = col_btn.button("Get recommendations", type="primary")
    if fetch:
        recs_data, err = get("/recommend", user_id=user_id, n=n_recs)
        if err:
            st.error(err)
        elif recs_data:
            v = recs_data.get("variant", "?")
            st.markdown(f"User **{user_id}** is in the " + variant_badge(v) +
                        f" variant · top {n_recs} items", unsafe_allow_html=True)
            recs = recs_data.get("recommendations", [])
            if not recs:
                st.warning("No recommendations returned.")
            else:
                df_r = pd.DataFrame(recs)
                st.altair_chart(
                    alt.Chart(df_r)
                    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                    .encode(
                        y=alt.Y("rank:O", sort="ascending",
                                axis=alt.Axis(title="Rank", labelExpr="'#' + datum.value")),
                        x=alt.X("score:Q", title="Score"),
                        color=alt.Color("algorithm:N", scale=alt.Scale(
                            domain=["collaborative_als", "content_based",
                                    "als_cold_start", "content_cold_start", "popularity_fallback"],
                            range=["#8b6f47", "#5aab6d", "#a89880", "#9e9488", "#c4a882"])),
                        tooltip=["rank:O", "item_id:Q", "score:Q", "algorithm:N"])
                    .properties(height=max(200, n_recs * 28), title="Score by Rank")
                    .configure_view(strokeWidth=0)
                    .configure_axis(grid=False, labelColor="#000000", titleColor="#000000")
                    .configure_title(color="#000000"),
                    use_container_width=True)
                st.subheader("Log a click")
                click_item = st.selectbox("Select item",
                    options=[r["item_id"] for r in recs],
                    format_func=lambda x: f"Item {x}")
                click_rank = next((r["rank"] for r in recs if r["item_id"] == click_item), None)
                if st.button("Log click", type="secondary"):
                    resp, err = post("/event", {
                        "experiment_id": recs_data["experiment_id"],
                        "user_id":  user_id,
                        "item_id":  click_item,
                        "rank":     click_rank,
                    })
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Click logged — item {click_item}, rank {click_rank}, "
                                   f"variant {resp.get('variant', '?')}")
                with st.expander("Raw list"):
                    st.dataframe(df_r, use_container_width=True)

with tab_variant:
    st.header("Variant Lookup")
    st.caption("GET /variant — no impression logged.")
    col_a, col_b = st.columns([2, 1])
    lookup_uid = col_a.number_input("User ID", min_value=0, max_value=99999, value=0, step=1, key="luid")
    col_b.markdown("<br>", unsafe_allow_html=True)
    if col_b.button("Check variant", type="primary"):
        vdata, err = get("/variant", user_id=lookup_uid)
        if err:
            st.error(err)
        elif vdata:
            st.markdown(f"User **{lookup_uid}** -> " + variant_badge(vdata.get("variant", "?")),
                        unsafe_allow_html=True)
    st.divider()
    st.subheader("Bulk variant sweep")
    col_lo, col_hi, col_sw = st.columns([1, 1, 1])
    sweep_lo = col_lo.number_input("From user ID", value=0,  min_value=0, key="slo")
    sweep_hi = col_hi.number_input("To user ID",   value=99, min_value=1, key="shi")
    col_sw.markdown("<br>", unsafe_allow_html=True)
    if col_sw.button("Run sweep", type="secondary"):
        if sweep_hi - sweep_lo > 500:
            st.warning("Limit range to 500 users max.")
        else:
            results = []
            prog  = st.progress(0, text="Fetching...")
            total = sweep_hi - sweep_lo + 1
            for i, uid in enumerate(range(int(sweep_lo), int(sweep_hi) + 1)):
                vd, _ = get("/variant", user_id=uid)
                results.append({"user_id": uid, "variant": vd["variant"] if vd else "error"})
                prog.progress((i + 1) / total, text=f"User {uid}...")
            prog.empty()
            sweep_df = pd.DataFrame(results)
            counts = sweep_df["variant"].value_counts().reset_index()
            counts.columns = ["variant", "count"]
            counts["pct"] = counts["count"] / counts["count"].sum()
            c1, c2 = st.columns(2)
            with c1:
                st.altair_chart(
                    alt.Chart(counts).mark_arc(innerRadius=50)
                    .encode(
                        theta="count:Q",
                        color=alt.Color("variant:N", scale=alt.Scale(
                            domain=["control", "treatment"],
                            range=["#8b6f47", "#5aab6d"])),
                        tooltip=["variant:N", "count:Q", alt.Tooltip("pct:Q", format=".1%")])
                    .properties(title="Split distribution", height=200)
                    .configure_title(color="#000000"),
                    use_container_width=True)
            with c2:
                st.dataframe(
                    counts.assign(pct=counts["pct"].map("{:.1%}".format))
                          .rename(columns={"variant": "Variant", "count": "Users", "pct": "Share"}),
                    use_container_width=True, hide_index=True)
