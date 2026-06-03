from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from core.validator import ValidationResult


class ReadinessScorer:
    PENALTY_WEIGHTS = {
        "NULL": 0.5,
        "TYPE": 0.4,
        "REFERENCE": 0.4,
        "DUPLICATE": 0.3,
        "FORMAT": 0.2,
        "RANGE": 0.2,
    }

    SCORE_BANDS = {
        (90, 100): ("MIGRATION READY", "#10B981", "🟢"),
        (75, 89): ("MINOR FIXES NEEDED", "#84CC16", "🟡"),
        (50, 74): ("SIGNIFICANT ISSUES", "#F59E0B", "🟠"),
        (0, 49): ("NOT READY — MAJOR CLEANUP", "#EF4444", "🔴"),
    }

    def calculate(self, validation_result: ValidationResult) -> dict:
        total = validation_result.total_rows
        if total == 0:
            return {
                "score": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "band_label": "NOT READY — MAJOR CLEANUP",
                "color": "#EF4444",
                "emoji": "🔴",
                "penalty_breakdown": {},
                "column_impact": {},
            }

        error_row_indices = {e.row_number for e in validation_result.errors}
        invalid_count = len(error_row_indices)
        valid_count = total - invalid_count

        base_score = (valid_count / total) * 100

        penalty = 0.0
        penalties: Dict[str, float] = defaultdict(float)
        column_impact: Dict[str, float] = defaultdict(float)
        for error in validation_result.errors:
            weight = self.PENALTY_WEIGHTS.get(error.error_type, 0.1)
            penalty += weight
            penalties[error.error_type] += weight
            column_impact[error.column_name] += weight

        scaled_penalty = min((penalty / total) * 10, 40)
        final_score = max(0.0, min(100.0, base_score - scaled_penalty))
        final_score = round(final_score, 1)

        band_label, color, emoji = self._pick_band(final_score)
        column_impact_pct = {k: round((v / total) * 10, 2) for k, v in column_impact.items()}

        return {
            "score": final_score,
            "valid_rows": valid_count,
            "invalid_rows": invalid_count,
            "band_label": band_label,
            "color": color,
            "emoji": emoji,
            "penalty_breakdown": dict(penalties),
            "column_impact": dict(sorted(column_impact_pct.items(), key=lambda x: x[1], reverse=True)),
        }

    def _pick_band(self, score: float) -> tuple:
        for (low, high), value in self.SCORE_BANDS.items():
            if low <= score <= high:
                return value
        return ("NOT READY — MAJOR CLEANUP", "#EF4444", "🔴")

    def get_fix_suggestions(self, validation_result: ValidationResult, column_impact: dict) -> List[dict]:
        grouped: Dict[tuple, int] = defaultdict(int)
        for err in validation_result.errors:
            grouped[(err.column_name, err.error_type)] += 1
        items = []
        for (column, error_type), count in grouped.items():
            score_gain = round(column_impact.get(column, 0.0), 2)
            items.append(
                {
                    "column": column,
                    "error_type": error_type,
                    "error_count": count,
                    "score_gain": score_gain,
                    "fix_instruction": self._instruction(error_type, column),
                }
            )
        return sorted(items, key=lambda x: x["score_gain"], reverse=True)[:5]

    def _instruction(self, error_type: str, column: str) -> str:
        mapping = {
            "NULL": f"Populate missing values in {column} from source-of-truth lookups.",
            "TYPE": f"Normalize {column} to the expected data type before migration.",
            "REFERENCE": f"Resolve invalid foreign keys in {column} against master data.",
            "DUPLICATE": f"Deduplicate {column} records with merge rules.",
            "FORMAT": f"Apply pattern standardization for {column}.",
            "RANGE": f"Review and correct out-of-range values in {column}.",
        }
        return mapping.get(error_type, f"Fix data quality issues in {column}.")
