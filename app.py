"""
Sales Analysis Streamlit Application
=====================================
Live-connected to the company Sales Data Google Sheet (Sheet1):
    Year, Month, Item No., Item Description, Customer Code, Customer Name,
    Quantity, Sales Amt, Gross Profit (currency), Gross Profit,
    Gross Profit %, Column1, Zone

Four sections, selectable from the sidebar on the RIGHT of the screen:
    1. Zone Wise Sale Analysis
    2. Item Wise Sales Analysis
    3. Sales % Contribution Analysis
    4. Sales % with Time Analysis

Run with:  streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import (
    ALL_SALES_LABEL,
    ALL_ZONES_LABEL,
    SALES_TYPE_OPTIONS,
    TIME_FRAME_OPTIONS,
    PERIOD_COL,
    filter_by_sales_type,
    filter_by_zone,
    get_period_order,
    load_dataframe_from_url,
    prepare_dataframe,
)

# ---------------------------------------------------------------------------
# Fixed data source — your live Google Sheet. No upload / link entry needed.
# To point this app at a different sheet, just change the URL below.
# ---------------------------------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1vXveJ2TUXeeyWg5DO2aYe-7yfmEc3Azau4g1NghNQDo/edit?gid=0#gid=0"
CACHE_TTL_SECONDS = 300  # data refreshes automatically every 5 minutes

ACCENT = "#2E5AAC"
CHART_COLORWAY = ["#2E5AAC", "#E8833A", "#3FA672", "#B23B5E", "#7B5EA7", "#4FA8C9"]

st.set_page_config(
    page_title="Sales Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global styling: a cleaner, more "designed" look.
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
        html, body, [class*="css"] {{
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}

        /* --- Page header banner --- */
        .app-header {{
            background: linear-gradient(90deg, {ACCENT} 0%, #4A78C9 100%);
            padding: 1.4rem 1.8rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 1.4rem;
        }}
        .app-header h1 {{
            margin: 0;
            font-size: 1.6rem;
            font-weight: 700;
        }}
        .app-header p {{
            margin: 0.25rem 0 0 0;
            opacity: 0.9;
            font-size: 0.92rem;
        }}

        /* --- Section header --- */
        .section-title {{
            font-size: 1.35rem;
            font-weight: 700;
            color: #1F2A44;
            margin-bottom: 0.1rem;
        }}
        .section-caption {{
            color: #5B6472;
            font-size: 0.92rem;
            margin-bottom: 1.1rem;
        }}

        /* --- Metric cards --- */
        div[data-testid="stMetric"] {{
            background: #F7F9FC;
            border: 1px solid #E7EBF2;
            border-radius: 10px;
            padding: 0.9rem 1rem 0.6rem 1rem;
        }}
        div[data-testid="stMetricLabel"] {{
            font-weight: 600;
            color: #5B6472;
        }}

        /* --- Sidebar nav radio buttons look like nav items --- */
        section[data-testid="stSidebar"] .stRadio > label {{
            font-weight: 600;
        }}
    </style>

    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading — cached, auto-refreshing, live from the Google Sheet above.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Connecting to live sales sheet…")
def get_data(url: str):
    raw = load_dataframe_from_url(url)
    return prepare_dataframe(raw)


with st.sidebar:
    st.markdown("### 📊 Sales Analysis")
    st.caption("Connected to the live Sales Data sheet.")
    if st.button("🔄 Refresh Data", use_container_width=True):
        get_data.clear()
        st.rerun()

try:
    df = get_data(SHEET_URL)
    load_error = None
except Exception as e:
    df = None
    load_error = e

with st.sidebar:
    if df is not None:
        st.caption(f"Last loaded: {datetime.now().strftime('%b %d, %Y • %I:%M %p')}")
    st.markdown("---")
    st.markdown("#### Sections")
    section = st.radio(
        "Go to:",
        [
            "1. Zone Wise Sale Analysis",
            "2. Item Wise Sales Analysis",
            "3. Sales % Contribution Analysis",
            "4. Sales % with Time Analysis",
        ],
        label_visibility="collapsed",
    )

st.markdown(
    """
    <div class="app-header">
        <h1>📊 Sales Analysis Dashboard</h1>
        <p>Zone, item, and customer-level sales performance — live from the company Sales Data sheet.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if load_error is not None:
    st.error(
        "Could not load the live sheet. Make sure its General access is set "
        "to **'Anyone with the link' (Viewer)** in Google Sheets' Share "
        f"dialog, then click **Refresh Data**.\n\nDetails: {load_error}"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
px.defaults.color_discrete_sequence = CHART_COLORWAY
px.defaults.template = "plotly_white"


def zone_options(frame: pd.DataFrame):
    return [ALL_ZONES_LABEL] + sorted(frame["Zone"].dropna().unique().tolist())


def line_chart_with_labels(plot_df, x_col, y_col, title, y_label, text_fmt=None):
    """Plotly line chart with the value shown at each point, styled to match
    the rest of the dashboard."""
    if text_fmt is None:
        text_fmt = lambda v: f"{v:,.0f}"
    plot_df = plot_df.copy()
    plot_df["_label"] = plot_df[y_col].apply(text_fmt)

    fig = px.line(
        plot_df, x=x_col, y=y_col, markers=True, text="_label", title=title,
    )
    fig.update_traces(
        line=dict(width=3, color=ACCENT),
        marker=dict(size=8, color=ACCENT),
        textposition="top center",
        textfont=dict(size=11, color="#1F2A44"),
    )
    fig.update_layout(
        xaxis_title="Time Frame",
        yaxis_title=y_label,
        hovermode="x unified",
        title_font=dict(size=16, color="#1F2A44"),
        plot_bgcolor="white",
        margin=dict(t=60, l=10, r=10, b=10),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF1F6")
    return fig


def section_header(title: str, caption: str = ""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


# ===========================================================================
# SECTION 1: Zone Wise Sale Analysis
# ===========================================================================
if section.startswith("1."):
    section_header(
        "🗺️ Zone Wise Sale Analysis",
        "Total sales trend for a chosen Sales Type and Zone, over time.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        sales_type = st.selectbox("Sales Type", SALES_TYPE_OPTIONS, key="s1_type")
    with c2:
        zone = st.selectbox("Zone", zone_options(df), key="s1_zone")
    with c3:
        time_frame = st.selectbox("Time Frame", TIME_FRAME_OPTIONS, key="s1_tf")

    filtered = filter_by_sales_type(df, sales_type)
    filtered = filter_by_zone(filtered, zone)

    if filtered.empty:
        st.warning("No data for this selection.")
    else:
        period_col = PERIOD_COL[time_frame]
        period_order = get_period_order(filtered, time_frame)

        agg = (
            filtered.groupby(period_col, as_index=False)["Sales Amt"]
            .sum()
            .rename(columns={"Sales Amt": "Sales"})
        )
        agg[period_col] = pd.Categorical(agg[period_col], categories=period_order, ordered=True)
        agg = agg.sort_values(period_col)

        title = f"Sales Trend — {sales_type} — {zone} ({time_frame})"
        fig = line_chart_with_labels(agg, period_col, "Sales", title, "Sales Amt")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("View underlying data"):
            st.dataframe(agg, use_container_width=True)


# ===========================================================================
# SECTION 2: Item Wise Sales Analysis
# ===========================================================================
elif section.startswith("2."):
    section_header(
        "📦 Item Wise Sales Analysis",
        "Sales trend for a specific item, scoped to a Zone and Sales Type.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        zone = st.selectbox("Zone", zone_options(df), key="s2_zone")
    with c2:
        sales_type = st.selectbox("Sales Type", SALES_TYPE_OPTIONS, key="s2_type")
    with c3:
        time_frame = st.selectbox("Time Frame", TIME_FRAME_OPTIONS, key="s2_tf")

    scoped = filter_by_zone(df, zone)
    scoped = filter_by_sales_type(scoped, sales_type)

    item_options = sorted(scoped["Item Description"].dropna().unique().tolist())
    if not item_options:
        st.warning("No items available for this Zone / Sales Type combination.")
    else:
        item_desc = st.selectbox("Item Description", item_options, key="s2_item")
        item_df = scoped[scoped["Item Description"] == item_desc]

        period_col = PERIOD_COL[time_frame]
        period_order = get_period_order(item_df, time_frame)

        agg = (
            item_df.groupby(period_col, as_index=False)["Sales Amt"]
            .sum()
            .rename(columns={"Sales Amt": "Sales"})
        )
        agg[period_col] = pd.Categorical(agg[period_col], categories=period_order, ordered=True)
        agg = agg.sort_values(period_col)

        title = f"Sales Trend — {item_desc} — {zone} ({time_frame})"
        fig = line_chart_with_labels(agg, period_col, "Sales", title, "Sales Amt")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("View underlying data"):
            st.dataframe(agg, use_container_width=True)


# ===========================================================================
# SECTION 3: Sales % Contribution Analysis
# ===========================================================================
elif section.startswith("3."):
    section_header(
        "📊 Sales Percentage Contribution Analysis",
        "Each cell = a customer's Sales Amt ÷ total Sales Amt of the selected "
        "Zone & Sales Type, for that period. Columns sum to 100%.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        sales_type = st.selectbox("Sales Type", SALES_TYPE_OPTIONS, key="s3_type")
    with c2:
        time_frame = st.selectbox("Time Frame", TIME_FRAME_OPTIONS, key="s3_tf")
    with c3:
        zone = st.selectbox("Zone", zone_options(df), key="s3_zone")

    scoped = filter_by_sales_type(df, sales_type)
    scoped = filter_by_zone(scoped, zone)

    if scoped.empty:
        st.warning("No data for this selection.")
    else:
        period_col = PERIOD_COL[time_frame]
        period_order = get_period_order(scoped, time_frame)

        cust_period = (
            scoped.groupby(["Customer Display", period_col], as_index=False)["Sales Amt"]
            .sum()
        )
        period_totals = scoped.groupby(period_col)["Sales Amt"].sum()

        pivot = cust_period.pivot(index="Customer Display", columns=period_col, values="Sales Amt").fillna(0.0)
        pivot = pivot.reindex(columns=period_order)

        pct_table = pivot.div(period_totals.reindex(period_order), axis=1) * 100
        pct_table = pct_table.round(2)

        # Sort customers by their average contribution, descending
        pct_table = pct_table.loc[pct_table.mean(axis=1).sort_values(ascending=False).index]

        st.dataframe(
            pct_table.style.format("{:.2f}%").background_gradient(cmap="Blues", axis=None),
            use_container_width=True,
        )

        total_row = pd.DataFrame(
            [pct_table.sum(axis=0)], index=["Total (check = 100%)"]
        )
        st.caption("Column totals (sanity check):")
        st.dataframe(total_row.style.format("{:.2f}%"), use_container_width=True)


# ===========================================================================
# SECTION 4: Sales % with Time Analysis
# ===========================================================================
elif section.startswith("4."):
    section_header(
        "📈 Sales Percentage with Time Analysis",
        "Line = selected customer's Sales Amt ÷ total Sales Amt for the "
        "selected Sales Type & Zone, tracked over the selected Time Frame.",
    )

    c1, c2 = st.columns(2)
    with c1:
        time_frame = st.selectbox("Time Frame", TIME_FRAME_OPTIONS, key="s4_tf")
    with c2:
        zone = st.selectbox("Zone", zone_options(df), key="s4_zone")

    c3, c4 = st.columns(2)
    with c3:
        sales_type = st.selectbox("Sales Type", SALES_TYPE_OPTIONS, key="s4_type")

    scoped_for_customers = filter_by_zone(df, zone)
    scoped_for_customers = filter_by_sales_type(scoped_for_customers, sales_type)
    customer_map = (
        scoped_for_customers[["Customer Code", "Customer Display"]]
        .drop_duplicates()
        .sort_values("Customer Display")
    )

    with c4:
        if customer_map.empty:
            st.warning("No customers for this Zone / Sales Type.")
            st.stop()
        customer_display = st.selectbox(
            "Customer Code", customer_map["Customer Display"].tolist(), key="s4_cust"
        )

    scoped = filter_by_sales_type(df, sales_type)
    scoped = filter_by_zone(scoped, zone)

    period_col = PERIOD_COL[time_frame]
    period_order = get_period_order(scoped, time_frame)

    period_totals = scoped.groupby(period_col)["Sales Amt"].sum().reindex(period_order).fillna(0.0)
    cust_scoped = scoped[scoped["Customer Display"] == customer_display]
    cust_by_period = cust_scoped.groupby(period_col)["Sales Amt"].sum().reindex(period_order).fillna(0.0)

    pct_series = (cust_by_period / period_totals.replace(0, pd.NA)) * 100
    pct_series = pct_series.fillna(0.0)

    plot_df = pd.DataFrame({
        period_col: period_order,
        "Contribution %": pct_series.values,
    })
    plot_df[period_col] = pd.Categorical(plot_df[period_col], categories=period_order, ordered=True)

    title = f"{customer_display} — % of {sales_type} Sales in {zone} ({time_frame})"
    fig = line_chart_with_labels(
        plot_df, period_col, "Contribution %", title, "Contribution %",
        text_fmt=lambda v: f"{v:.1f}%",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View underlying data"):
        st.dataframe(plot_df, use_container_width=True)
