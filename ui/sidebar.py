from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from utils.sample_data_generator import build_sample_schema, build_sample_source


def render_sidebar() -> int:
    with st.sidebar:
        st.markdown('<div class="df-brand">DATAFORGE</div><div class="df-tagline">Purify. Validate. Migrate.</div>', unsafe_allow_html=True)
        steps = ["Upload Files", "Map Columns", "Run Validation", "View Results", "Export Reports"]
        current = st.session_state.current_step
        for idx, step in enumerate(steps, start=1):
            cls = "step-done" if idx < current else "step-current" if idx == current else "step-future"
            label = "✓" if idx < current else str(idx)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0;"><span class="step-dot {cls}">{label}</span><span>{step}</span></div>',
                unsafe_allow_html=True,
            )
        if st.button("Load Sample Data", use_container_width=True):
            try:
                root = Path(__file__).resolve().parents[1]
                source_path = root / "sample_data" / "sample_source.xlsx"
                schema_path = root / "sample_data" / "sample_schema.xlsx"
                if source_path.exists() and schema_path.exists():
                    st.session_state.uploaded_df = pd.read_excel(source_path)
                    st.session_state.schema_df = pd.read_excel(schema_path)
                else:
                    st.session_state.uploaded_df = build_sample_source()
                    st.session_state.schema_df = build_sample_schema()
                st.session_state.uploaded_filename = "sample_source.xlsx"
                st.session_state.demo_mode = True
                st.session_state.current_step = 2
                st.toast("Demo data loaded — 500 rows, 155 injected errors")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not load sample files. {exc}")
        with st.expander("How It Works"):
            st.markdown(
                """
- Upload your Excel/CSV source file and target schema
- Map source columns to target fields — auto-matching included
- Run 6-dimension validation and download clean migration report
"""
            )
        st.markdown("<div style='margin-top:2rem;color:#6B7280;font-size:12px;'>DataForge v1.0  |  Built with Streamlit</div>", unsafe_allow_html=True)
    return current
