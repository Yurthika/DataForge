from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

import pandas as pd


@dataclass
class ValidationError:
    row_number: int
    column_name: str
    actual_value: Any
    error_type: str
    error_message: str
    severity: str
    suggested_fix: str


@dataclass
class ValidationResult:
    total_rows: int
    valid_row_indices: list
    invalid_row_indices: list
    errors: List[ValidationError]
    error_counts_by_type: dict
    error_counts_by_column: dict


class ValidationEngine:
    def run_all(self, df: pd.DataFrame, schema_df: pd.DataFrame, mappings: Dict[str, str]) -> ValidationResult:
        if df.empty:
            return ValidationResult(0, [], [], [], {}, {})
        reverse_map = {target: source for source, target in mappings.items() if target and target != "-- Skip --"}
        schema = schema_df.copy()
        required_fields = schema.loc[schema["required"] == "Y", "field_name"].tolist()
        required_source_cols = [reverse_map[f] for f in required_fields if f in reverse_map]
        null_errors = self.check_null_values(df, required_source_cols)
        null_block: Set[Tuple[int, str]] = {(e.row_number - 1, e.column_name) for e in null_errors}
        type_errors = self.check_data_types(df, schema, reverse_map, null_block)
        format_errors = self.check_format_patterns(df, schema, reverse_map, null_block)
        range_errors = self.check_range_values(df, schema, reverse_map, null_block)
        key_fields = [reverse_map["contact_id"]] if "contact_id" in reverse_map else []
        duplicate_errors = self.check_duplicates(df, key_fields)
        reference_errors = self.check_referential_integrity(df, schema, reverse_map)
        errors = null_errors + type_errors + format_errors + range_errors + duplicate_errors + reference_errors
        invalid_rows = sorted({e.row_number - 1 for e in errors})
        valid_rows = [idx for idx in range(len(df)) if idx not in set(invalid_rows)]
        by_type: Dict[str, int] = {}
        by_column: Dict[str, int] = {}
        for err in errors:
            by_type[err.error_type] = by_type.get(err.error_type, 0) + 1
            by_column[err.column_name] = by_column.get(err.column_name, 0) + 1
        return ValidationResult(len(df), valid_rows, invalid_rows, errors, by_type, by_column)

    def check_null_values(self, df: pd.DataFrame, required_fields: List[str]) -> List[ValidationError]:
        errors: List[ValidationError] = []
        for field in required_fields:
            if field not in df.columns:
                continue
            mask = df[field].isna() | (df[field].astype(str).str.strip() == "")
            for idx in df[mask].index:
                errors.append(
                    ValidationError(
                        row_number=idx + 1,
                        column_name=field,
                        actual_value=df.at[idx, field],
                        error_type="NULL",
                        error_message=f"Missing required value in {field}",
                        severity="Critical",
                        suggested_fix=f"Fill in missing {field} value",
                    )
                )
        return errors

    def check_data_types(
        self, df: pd.DataFrame, schema_df: pd.DataFrame, reverse_map: Dict[str, str], null_block: Set[Tuple[int, str]]
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        required_fields = set(schema_df.loc[schema_df["required"] == "Y", "field_name"].tolist())
        for _, row in schema_df.iterrows():
            target = row["field_name"]
            source = reverse_map.get(target)
            if not source or source not in df.columns:
                continue
            expected = str(row["data_type"]).lower()
            for idx, value in df[source].items():
                if (idx, source) in null_block:
                    continue
                if pd.isna(value):
                    continue
                ok = True
                try:
                    if expected == "integer":
                        int(float(value))
                    elif expected == "float":
                        float(value)
                    elif expected == "date":
                        pd.to_datetime(value, dayfirst=True, errors="raise")
                    else:
                        str(value)
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    sev = "Critical" if target in required_fields else "Warning"
                    errors.append(
                        ValidationError(
                            row_number=idx + 1,
                            column_name=source,
                            actual_value=value,
                            error_type="TYPE",
                            error_message=f"Expected {expected} for {source}",
                            severity=sev,
                            suggested_fix=f"Convert {value} to {expected}",
                        )
                    )
        return errors

    def check_format_patterns(
        self, df: pd.DataFrame, schema_df: pd.DataFrame, reverse_map: Dict[str, str], null_block: Set[Tuple[int, str]]
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        builtins = {
            "email": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            "phone": r"^(\+91-\d{5}-\d{5}|\d{10})$",
            "pincode": r"^\d{6}$",
            "created_date": r"^\d{2}/\d{2}/\d{4}$",
        }
        for _, row in schema_df.iterrows():
            target = row["field_name"]
            source = reverse_map.get(target)
            if not source or source not in df.columns:
                continue
            schema_type = str(row.get("data_type", "")).lower()
            if schema_type in ["integer", "float", "int"]:
                continue
            regex = row.get("format_regex") if isinstance(row.get("format_regex"), str) else ""
            pattern = regex or builtins.get(target, "")
            if not pattern:
                continue
            for idx, value in df[source].items():
                if (idx, source) in null_block or pd.isna(value):
                    continue
                text = str(value).strip()
                if not re.match(pattern, text):
                    errors.append(
                        ValidationError(
                            row_number=idx + 1,
                            column_name=source,
                            actual_value=value,
                            error_type="FORMAT",
                            error_message=f"Invalid format for {source}",
                            severity="Warning",
                            suggested_fix=f"Correct format to {pattern}",
                        )
                    )
        return errors

    def check_range_values(
        self, df: pd.DataFrame, schema_df: pd.DataFrame, reverse_map: Dict[str, str], null_block: Set[Tuple[int, str]]
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        for _, row in schema_df.iterrows():
            target = row["field_name"]
            source = reverse_map.get(target)
            if not source or source not in df.columns:
                continue
            min_v = row.get("min_val")
            max_v = row.get("max_val")
            has_rule = not pd.isna(min_v) or not pd.isna(max_v) or target in {"annual_revenue", "age"}
            if not has_rule:
                continue
            for idx, value in df[source].items():
                if (idx, source) in null_block or pd.isna(value):
                    continue
                try:
                    num = float(value)
                except Exception:  # noqa: BLE001
                    continue
                critical = False
                out = False
                if not pd.isna(min_v) and num < float(min_v):
                    out = True
                if not pd.isna(max_v) and num > float(max_v):
                    out = True
                if target == "annual_revenue" and num < 0:
                    out = True
                if target == "age" and (num < 18 or num > 65):
                    out = True
                    if num > 120:
                        critical = True
                if out:
                    errors.append(
                        ValidationError(
                            row_number=idx + 1,
                            column_name=source,
                            actual_value=value,
                            error_type="RANGE",
                            error_message=f"Value {value} is outside allowed range",
                            severity="Critical" if critical else "Warning",
                            suggested_fix=f"Value {value} is outside allowed range {min_v}–{max_v}",
                        )
                    )
        return errors

    def check_duplicates(self, df: pd.DataFrame, key_fields: List[str]) -> List[ValidationError]:
        errors: List[ValidationError] = []
        if not key_fields or any(k not in df.columns for k in key_fields):
            return errors
        grouped = df.groupby(key_fields, dropna=False).indices
        group_id = 1
        for key, indices in grouped.items():
            if len(indices) <= 1:
                continue
            key_val = key if isinstance(key, tuple) else (key,)
            for idx in indices:
                errors.append(
                    ValidationError(
                        row_number=idx + 1,
                        column_name=key_fields[0],
                        actual_value=key_val[0],
                        error_type="DUPLICATE",
                        error_message=f"Duplicate key in group {group_id}",
                        severity="Critical",
                        suggested_fix=f"Remove or merge duplicate record with contact_id {key_val[0]}",
                    )
                )
            group_id += 1
        return errors

    def check_referential_integrity(self, df: pd.DataFrame, schema_df: pd.DataFrame, reverse_map: Dict[str, str]) -> List[ValidationError]:
        errors: List[ValidationError] = []
        valid_managers = set(range(1001, 1121))
        fk_rows = schema_df[schema_df["reference_table"].fillna("") != ""]
        for _, row in fk_rows.iterrows():
            target = row["field_name"]
            source = reverse_map.get(target)
            if not source or source not in df.columns:
                continue
            for idx, value in df[source].items():
                if pd.isna(value):
                    continue
                try:
                    int_val = int(float(value))
                except Exception:  # noqa: BLE001
                    continue
                if int_val not in valid_managers:
                    errors.append(
                        ValidationError(
                            row_number=idx + 1,
                            column_name=source,
                            actual_value=value,
                            error_type="REFERENCE",
                            error_message=f"{source} {value} missing in master table",
                            severity="Critical",
                            suggested_fix=f"account_manager_id {value} does not exist — assign a valid manager",
                        )
                    )
        return errors
