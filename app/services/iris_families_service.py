"""
app/services/iris_families_service.py
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_NUM_COLS = (
    "pop_15p", "pop_15_24", "pop_25_54", "pop_55_79", "pop_80p",
    "pop_15p_alone", "pop_15_24_alone", "pop_25_54_alone",
    "pop_55_79_alone", "pop_80p_alone",
    "families", "couples_with_children", "single_parent", "couples_no_children",
    "families_0_children", "families_1_child", "families_2_children",
    "families_3_children", "families_4p_children",
)

_SELECT = """
    SELECT iris_code, com_code, iris_name, dep_code, reg_code, year,
           pop_15p, pop_15_24, pop_25_54, pop_55_79, pop_80p,
           pop_15p_alone, pop_15_24_alone, pop_25_54_alone,
           pop_55_79_alone, pop_80p_alone,
           families, couples_with_children, single_parent, couples_no_children,
           families_0_children, families_1_child, families_2_children,
           families_3_children, families_4p_children
    FROM iris_families
"""


def _safe_float(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _row_to_dict(row) -> dict:
    return {
        "iris_code": row.iris_code,
        "iris_name": row.iris_name,
        "com_code":  row.com_code,
        "dep_code":  row.dep_code,
        "reg_code":  row.reg_code,
        "year":      row.year,
        **{col: _safe_float(getattr(row, col)) for col in _NUM_COLS},
    }


class IrisFamiliesService:

    @lru_cache(maxsize=1)
    def get_available_years(self) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT DISTINCT year FROM iris_families ORDER BY year")
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            db.close()

    def get_latest_year(self) -> Optional[int]:
        years = self.get_available_years()
        return max(years) if years else None

    def _resolve_year(self, year: Optional[int]) -> Optional[int]:
        return year if year is not None else self.get_latest_year()

    # ── Par code IRIS ──────────────────────────────────────────────────────────
    def get_by_iris(self, iris_code: str, year: Optional[int] = None) -> Optional[dict]:
        resolved_year = self._resolve_year(year)
        if resolved_year is None:
            return None
        db = SessionLocal()
        try:
            sql = text(f"{_SELECT} WHERE iris_code = :iris_code AND year = :year LIMIT 1")
            row = db.execute(sql, {"iris_code": iris_code, "year": resolved_year}).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            db.close()

    # ── Par commune ─────────────────────────────────────────────────────────────
    @lru_cache(maxsize=1024)
    def get_by_commune(self, com_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text(f"{_SELECT} WHERE com_code = :com_code AND year = :year ORDER BY iris_code")
            rows = db.execute(sql, {"com_code": com_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {
                "com_code":   com_code,
                "year":       resolved_year,
                "total_iris": len(iris_list),
                "iris_list":  iris_list,
            }
        finally:
            db.close()

    # ── Par EPCI ────────────────────────────────────────────────────────────────
    @lru_cache(maxsize=512)
    def get_by_epci(self, epci_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text(f"""
                SELECT if.iris_code, if.com_code, if.iris_name, if.dep_code, if.reg_code, if.year,
                       if.pop_15p, if.pop_15_24, if.pop_25_54, if.pop_55_79, if.pop_80p,
                       if.pop_15p_alone, if.pop_15_24_alone, if.pop_25_54_alone,
                       if.pop_55_79_alone, if.pop_80p_alone,
                       if.families, if.couples_with_children, if.single_parent, if.couples_no_children,
                       if.families_0_children, if.families_1_child, if.families_2_children,
                       if.families_3_children, if.families_4p_children
                FROM iris_families if
                JOIN geo_codes gc ON gc.codgeo = if.com_code
                WHERE gc.epci = :epci_code AND if.year = :year
                ORDER BY if.com_code, if.iris_code
            """)
            rows = db.execute(sql, {"epci_code": epci_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {
                "epci_code":  epci_code,
                "year":       resolved_year,
                "total_iris": len(iris_list),
                "iris_list":  iris_list,
            }
        finally:
            db.close()

    # ── Par département ─────────────────────────────────────────────────────────
    @lru_cache(maxsize=200)
    def get_by_department(self, dep_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text(f"{_SELECT} WHERE dep_code = :dep_code AND year = :year ORDER BY com_code, iris_code")
            rows = db.execute(sql, {"dep_code": dep_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {
                "dep_code":   dep_code,
                "year":       resolved_year,
                "total_iris": len(iris_list),
                "iris_list":  iris_list,
            }
        finally:
            db.close()

    # ── Par région ──────────────────────────────────────────────────────────────
    @lru_cache(maxsize=50)
    def get_by_region(self, reg_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text(f"{_SELECT} WHERE reg_code = :reg_code AND year = :year ORDER BY com_code, iris_code")
            rows = db.execute(sql, {"reg_code": reg_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {
                "reg_code":   reg_code,
                "year":       resolved_year,
                "total_iris": len(iris_list),
                "iris_list":  iris_list,
            }
        finally:
            db.close()
