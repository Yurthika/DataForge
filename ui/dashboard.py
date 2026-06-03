from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.validator import ValidationResult


def render_kpi_cards(total: int, valid: int, invalid: int, score: float, score_color: str) -> None:
    cards = [("📊", "Total Rows", str(total), "#F9FAFB"), ("✅", "Valid Rows", str(valid), "#10B981"), ("❌", "Invalid Rows", str(invalid), "#EF4444"), ("🎯", "Readiness Score", f"{score:.0f}%", score_color)]
    cols = st.columns(4)
    for col, (icon, label, value, color) in zip(cols, cards):
        with col:
            st.markdown(f"<div class='kpi-card'><div>{icon} {label}</div><div class='kpi-value' style='color:{color};'>{value}</div></div>", unsafe_allow_html=True)


def build_score_gauge(score: float, label: str, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=score, number={"suffix": "%"}, gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB", family="Inter"),
        margin=dict(l=20, r=20, t=30, b=50),
        annotations=[dict(text=f"<b style='color:{color}'>{label}</b>", x=0.5, y=-0.1, showarrow=False)],
    )
    return fig


def build_error_pie(validation_result: ValidationResult) -> go.Figure:
    color_map = {"NULL": "#EF4444", "TYPE": "#F59E0B", "FORMAT": "#8B5CF6", "DUPLICATE": "#3B82F6", "RANGE": "#10B981", "REFERENCE": "#EC4899"}
    data = pd.DataFrame({"error_type": list(validation_result.error_counts_by_type.keys()), "count": list(validation_result.error_counts_by_type.values())})
    if data.empty:
        data = pd.DataFrame({"error_type": ["NO_ERRORS"], "count": [1]})
        color_map["NO_ERRORS"] = "#10B981"
    fig = px.pie(data, names="error_type", values="count", color="error_type", color_discrete_map=color_map)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111827", font=dict(color="#F9FAFB", family="Inter"), legend={"x": 1.0, "y": 0.5})
    return fig


def build_column_heatmap(validation_result: ValidationResult, source_columns: List[str]) -> go.Figure:
    x_types = ["NULL", "TYPE", "FORMAT", "RANGE", "DUPLICATE", "REFERENCE"]
    matrix = []
    lookup = defaultdict(lambda: defaultdict(int))
    for err in validation_result.errors:
        lookup[err.column_name][err.error_type] += 1
    for col in source_columns:
        matrix.append([lookup[col][e] for e in x_types])
    fig = go.Figure(data=go.Heatmap(z=matrix, x=x_types, y=source_columns, colorscale=[[0, "#111827"], [0.2, "#7F1D1D"], [1, "#EF4444"]], hovertemplate="Column %{y} has %{z} %{x} errors<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111827", font=dict(color="#F9FAFB", family="Inter"))
    return fig


def render_error_table(validation_result: ValidationResult) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_types = st.multiselect("Filter by Error Type", options=sorted(validation_result.error_counts_by_type.keys()))
    with c2:
        severity = st.radio("Severity", ["All", "Critical", "Warning", "Info"], horizontal=True)
    with c3:
        search = st.text_input("Search by column name")
    rows = []
    for e in validation_result.errors:
        if selected_types and e.error_type not in selected_types:
            continue
        if severity != "All" and e.severity != severity:
            continue
        if search and search.lower() not in e.column_name.lower():
            continue
        rows.append({"Row #": e.row_number, "Field": e.column_name, "Actual Value": e.actual_value, "Error Type": e.error_type, "Severity": e.severity, "Suggested Fix": e.suggested_fix})
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No errors match current filters.")
        return
    page_size = 50
    total_pages = max(1, ceil(len(df) / page_size))
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    st.session_state.current_page = min(st.session_state.current_page, total_pages)
    start = (st.session_state.current_page - 1) * page_size
    page_df = df.iloc[start : start + page_size]
    style_rows = []
    for _, row in page_df.iterrows():
        bg = "rgba(239, 68, 68, 0.15)" if row["Severity"] == "Critical" else "rgba(245, 158, 11, 0.15)" if row["Severity"] == "Warning" else "rgba(59, 130, 246, 0.15)"
        style_rows.append(f"<tr style='background:{bg};'>" + "".join([f"<td style='padding:6px;border:1px solid #1F2937'>{row[col]}</td>" for col in page_df.columns]) + "</tr>")
    st.markdown("<table style='width:100%;border-collapse:collapse;'><thead><tr>" + "".join([f"<th style='padding:8px;background:#1F2937;border:1px solid #1F2937'>{c}</th>" for c in page_df.columns]) + "</tr></thead><tbody>" + "".join(style_rows) + "</tbody></table>", unsafe_allow_html=True)
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("Prev") and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
            st.rerun()
    with p2:
        st.markdown(f"<div style='text-align:center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
    with p3:
        if st.button("Next") and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1
            st.rerun()


def render_fix_impact_panel(fixes: List[dict]) -> None:
    st.subheader("Top 5 High-Impact Fixes")
    for i, item in enumerate(fixes, start=1):
        sev_color = "#EF4444" if item["error_type"] in {"NULL", "TYPE", "REFERENCE", "DUPLICATE"} else "#F59E0B"
        st.markdown(
            f"<div class='fix-card' style='border-left:4px solid {sev_color};display:flex;justify-content:space-between;'>"
            f"<div><b>{i}</b> • <b>{item['column']}</b> ({item['error_type']})</div>"
            f"<div>{item['error_count']} issues • <b>+{item['score_gain']:.2f}%</b> • {item['fix_instruction']}</div></div>",
            unsafe_allow_html=True,
        )
