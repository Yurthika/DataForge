from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from core.report_generator import ReportGenerator
from core.schema_mapper import SchemaMapper
from core.scorer import ReadinessScorer
from core.validator import ValidationEngine
from ui.dashboard import (
    build_column_heatmap,
    build_error_pie,
    build_score_gauge,
    render_error_table,
    render_fix_impact_panel,
    render_kpi_cards,
)
from ui.sidebar import render_sidebar
from ui.styles import get_styles
from utils.data_loader import parse_uploaded_file


st.set_page_config(page_title="DataForge — Purify. Validate. Migrate.", layout="wide")
st.markdown(get_styles(), unsafe_allow_html=True)

defaults = {
    "current_step": 1,
    "uploaded_df": None,
    "uploaded_filename": "",
    "schema_df": None,
    "column_mappings": {},
    "validation_result": None,
    "readiness_score": None,
    "demo_mode": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

mapper = SchemaMapper()
engine = ValidationEngine()
scorer = ReadinessScorer()
reporter = ReportGenerator()

render_sidebar()


def type_badge(dtype_name: str) -> str:
    return f"<span style='padding:2px 8px;border:1px solid #1F2937;background:#111827;font-size:12px;'>{dtype_name}</span>"


def step_1_upload() -> None:
    st.title("Step 1 — Upload Your Data")
    c1, c2 = st.columns(2)
    with c1:
        source_file = st.file_uploader("Upload Source File", type=["xlsx", "xls", "csv"])
        if source_file is not None:
            try:
                df, cols, dtypes, row_count, file_kb = parse_uploaded_file(source_file.name, source_file.getvalue())
                st.session_state.uploaded_df = df
                st.session_state.uploaded_filename = source_file.name
                st.success(f"✅ Loaded {row_count} rows × {len(cols)} columns")
                st.dataframe(df.head(10), use_container_width=True)
                st.caption(
                    f"Total Rows: {row_count}  |  Total Columns: {len(cols)}  |  File Size: {file_kb} KB\n\nDetected Types: "
                    + ", ".join([f"{k} ({v})" for k, v in dtypes.items()])
                )
                if row_count > 50000:
                    st.warning("Large file detected. Validation may take longer.")
            except ValueError as exc:
                st.error(str(exc))
    with c2:
        schema_option = st.selectbox(
            "Target Schema",
            ["Salesforce CRM (Preset)", "Generic Database (Preset)", "Upload Custom Schema"],
        )
        if schema_option == "Upload Custom Schema":
            schema_file = st.file_uploader("Upload Schema File", type=["xlsx", "xls"], key="schema_upload")
            if schema_file is not None:
                try:
                    st.session_state.schema_df = pd.read_excel(BytesIO(schema_file.getvalue()))
                    st.success("Schema uploaded successfully.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not parse schema file: {exc}")
        else:
            preset = "Salesforce CRM" if "Salesforce" in schema_option else "Generic Database"
            st.session_state.schema_df = mapper.load_preset_schema(preset)
            st.info(f"Using preset schema: {preset}")
            st.dataframe(st.session_state.schema_df, use_container_width=True)
    if st.button("Next: Map Columns →", disabled=st.session_state.uploaded_df is None):
        st.session_state.current_step = 2
        st.rerun()


def step_2_map() -> None:
    st.title("Step 2 — Map Source Columns to Target Fields")
    df = st.session_state.uploaded_df
    schema_df = st.session_state.schema_df
    if df is None or schema_df is None:
        st.error("Please complete Step 1 first.")
        return
    source_cols = df.columns.tolist()
    target_fields = schema_df["field_name"].tolist()
    required_fields = schema_df[schema_df["required"] == "Y"]["field_name"].tolist()
    if not st.session_state.column_mappings:
        st.session_state.column_mappings = {col: "-- Skip --" for col in source_cols}
    if st.button("Auto-Map All Columns"):
        auto = mapper.auto_map_columns(source_cols, target_fields)
        for s, t in auto.items():
            st.session_state.column_mappings[s] = t
    for i, src in enumerate(source_cols):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        selected = st.session_state.column_mappings.get(src, "-- Skip --")
        conf = 0.0 if selected == "-- Skip --" else mapper.calculate_confidence(src, selected)
        conf_color = "#10B981" if conf > 0.8 else "#F59E0B" if conf >= 0.5 else "#EF4444"
        with c1:
            st.markdown(f"`{src}` {type_badge(str(df[src].dtype).upper())}", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<span style='color:{conf_color};font-weight:700'>{conf*100:.0f}%</span>", unsafe_allow_html=True)
        with c3:
            st.session_state.column_mappings[src] = st.selectbox(
                f"Map `{src}`", ["-- Skip --"] + target_fields, index=(["-- Skip --"] + target_fields).index(selected) if selected in (["-- Skip --"] + target_fields) else 0, key=f"map_{i}"
            )
        with c4:
            req = "Required" if st.session_state.column_mappings[src] in required_fields else "Optional"
            badge = "#EF4444" if req == "Required" else "#6B7280"
            st.markdown(f"<span style='color:{badge}'>{req}</span>", unsafe_allow_html=True)
    missing = mapper.validate_mappings(st.session_state.column_mappings, required_fields)
    st.markdown(f"**{len(required_fields) - len(missing)} of {len(required_fields)} required fields mapped**")
    if missing:
        st.error(f"⚠️ {len(missing)} required fields unmapped: {', '.join(missing)}")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("← Back"):
            st.session_state.current_step = 1
            st.rerun()
    with b2:
        if st.button("Next: Run Validation →", disabled=bool(missing)):
            st.session_state.current_step = 3
            st.rerun()


@st.cache_data(show_spinner=False)
def run_validation_cached(df: pd.DataFrame, schema_df: pd.DataFrame, mappings: dict):
    return ValidationEngine().run_all(df, schema_df, mappings)


def step_3_validate() -> None:
    st.title("Step 3 — Run Validation")
    df = st.session_state.uploaded_df
    if df is None or st.session_state.schema_df is None:
        st.error("Please upload and map data first.")
        return
    st.write(f"Source file: `{st.session_state.uploaded_filename}`  |  Rows: `{len(df)}`  |  Mapped columns: `{len([v for v in st.session_state.column_mappings.values() if v != '-- Skip --'])}`")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("🚀 Run Validation", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()
            steps = [(0, "Initializing validation engine..."), (15, "Checking null values..."), (30, "Validating data types..."), (45, "Scanning format patterns..."), (60, "Detecting duplicate records..."), (75, "Validating value ranges..."), (90, "Verifying referential integrity..."), (100, "Calculating Migration Readiness Score...")]
            if len(df) > 10000:
                with st.spinner("Processing large file..."):
                    for p, t in steps:
                        progress.progress(p)
                        status.info(t)
                        time.sleep(0.5)
            else:
                for p, t in steps:
                    progress.progress(p)
                    status.info(t)
                    time.sleep(0.5)
            result = run_validation_cached(df, st.session_state.schema_df, st.session_state.column_mappings)
            score = scorer.calculate(result)
            st.session_state.validation_result = result
            st.session_state.readiness_score = score
            st.session_state.current_step = 4
            st.rerun()


def step_4_results() -> None:
    st.title("Step 4 — Validation Results")
    vr = st.session_state.validation_result
    sr = st.session_state.readiness_score
    if vr is None or sr is None:
        st.error("Run validation first.")
        return
    render_kpi_cards(vr.total_rows, len(vr.valid_row_indices), len(vr.invalid_row_indices), sr["score"], sr["color"])
    c1, c2 = st.columns(2)
    with c1:
        ph = st.empty()
        for i in range(int(sr["score"]) + 1):
            fig = build_score_gauge(i, sr["band_label"], sr["color"])
            ph.plotly_chart(fig, use_container_width=True)
            time.sleep(0.01)
    with c2:
        st.plotly_chart(build_error_pie(vr), use_container_width=True)
    st.plotly_chart(build_column_heatmap(vr, st.session_state.uploaded_df.columns.tolist()), use_container_width=True)
    render_error_table(vr)
    render_fix_impact_panel(scorer.get_fix_suggestions(vr, sr["column_impact"]))
    if st.button("Proceed to Export →"):
        st.session_state.current_step = 5
        st.rerun()


def step_5_export() -> None:
    st.title("Step 5 — Download Reports")
    vr = st.session_state.validation_result
    sr = st.session_state.readiness_score
    df = st.session_state.uploaded_df
    if vr is None or sr is None or df is None:
        st.error("Validation results not available.")
        return
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"### 📥 Valid Data Only\n{len(vr.valid_row_indices)} rows ready for migration")
        st.download_button("Download .xlsx", data=reporter.generate_valid_data_export(df, vr.valid_row_indices), file_name="dataforge_valid_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c2:
        st.markdown(f"### 📋 Error Report\n{len(vr.invalid_row_indices)} rows with {len(vr.errors)} errors logged")
        st.download_button("Download .xlsx", data=reporter.generate_error_report(df, vr), file_name="dataforge_error_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c3:
        st.markdown("### 📊 Full Validation Report\n5-sheet workbook with executive summary")
        st.download_button("Download .xlsx", data=reporter.generate_full_report(df, vr, sr), file_name="dataforge_full_validation_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    if st.button("🔄 Start New Validation"):
        for key, value in defaults.items():
            st.session_state[key] = value
        if "current_page" in st.session_state:
            del st.session_state["current_page"]
        st.rerun()


if st.session_state.current_step == 1:
    step_1_upload()
elif st.session_state.current_step == 2:
    step_2_map()
elif st.session_state.current_step == 3:
    step_3_validate()
elif st.session_state.current_step == 4:
    step_4_results()
else:
    step_5_export()
