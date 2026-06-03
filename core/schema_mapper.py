from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List

import pandas as pd


class SchemaMapper:
    def load_preset_schema(self, preset_name: str) -> pd.DataFrame:
        base = [
            ("contact_id", "integer", "Y", r"^\d+$", None, None, ""),
            ("first_name", "string", "N", "", None, None, ""),
            ("last_name", "string", "N", "", None, None, ""),
            ("email", "string", "Y", r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", None, None, ""),
            ("phone", "string", "Y", r"^(\+91-\d{5}-\d{5}|\d{10})$", None, None, ""),
            ("age", "integer", "N", "", 18, 65, ""),
            ("account_type", "string", "Y", r"^(Individual|Corporate|SME)$", None, None, ""),
            ("annual_revenue", "float", "Y", "", 0, None, ""),
            ("city", "string", "N", "", None, None, ""),
            ("pincode", "string", "N", r"^\d{6}$", None, None, ""),
            ("created_date", "date", "N", r"^\d{2}/\d{2}/\d{4}$", None, None, ""),
            ("account_manager_id", "integer", "N", r"^\d+$", None, None, "manager_master"),
        ]
        if preset_name == "Salesforce CRM":
            return pd.DataFrame(
                base,
                columns=["field_name", "data_type", "required", "format_regex", "min_val", "max_val", "reference_table"],
            )
        if preset_name == "Generic Database":
            generic = pd.DataFrame(
                base,
                columns=["field_name", "data_type", "required", "format_regex", "min_val", "max_val", "reference_table"],
            )
            generic["required"] = "N"
            return generic
        if preset_name == "Custom Upload":
            return pd.DataFrame(columns=["field_name", "data_type", "required", "format_regex", "min_val", "max_val", "reference_table"])
        raise ValueError("Unknown preset schema selected.")

    @staticmethod
    def _normalize(value: str) -> str:
        return value.lower().replace("_", "").replace(" ", "")

    def calculate_confidence(self, source_col: str, target_field: str) -> float:
        return SequenceMatcher(None, self._normalize(source_col), self._normalize(target_field)).ratio()

    def auto_map_columns(self, source_cols: List[str], target_fields: List[str]) -> Dict[str, str]:
        mappings: Dict[str, str] = {}
        remaining_targets = set(target_fields)
        for source in source_cols:
            scored = [(t, self.calculate_confidence(source, t)) for t in remaining_targets]
            if not scored:
                continue
            best_target, best_score = max(scored, key=lambda x: x[1])
            if best_score >= 0.6:
                mappings[source] = best_target
                remaining_targets.remove(best_target)
        return mappings

    def validate_mappings(self, mappings: Dict[str, str], required_fields: List[str]) -> List[str]:
        mapped_targets = {v for v in mappings.values() if v and v != "-- Skip --"}
        return [field for field in required_fields if field not in mapped_targets]
