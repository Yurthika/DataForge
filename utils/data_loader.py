from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


def _dtype_label(dtype: str) -> str:
    d = str(dtype).lower()
    if "int" in d:
        return "INT"
    if "float" in d:
        return "FLOAT"
    if "date" in d or "time" in d:
        return "DATE"
    return "STR"


@st.cache_data(show_spinner=False)
def parse_uploaded_file(file_name: str, file_bytes: bytes) -> Tuple[pd.DataFrame, List[str], Dict[str, str], int, float]:
    try:
        ext = file_name.lower().split(".")[-1]
        buffer = BytesIO(file_bytes)
        if ext == "csv":
            df = pd.read_csv(buffer)
        elif ext in {"xlsx", "xls"}:
            df = pd.read_excel(buffer)
        else:
            raise ValueError("Unsupported file format. Please upload .xlsx, .xls, or .csv")
        columns = df.columns.tolist()
        detected_types = {col: _dtype_label(dtype) for col, dtype in df.dtypes.items()}
        row_count = len(df)
        file_size_kb = round(len(file_bytes) / 1024, 2)
        return df, columns, detected_types, row_count, file_size_kb
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unable to parse the uploaded file. Please verify the format and content. Details: {exc}") from exc
