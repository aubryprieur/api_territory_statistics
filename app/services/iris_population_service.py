"""
app/services/iris_population_service.py
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_NUM_COLS = (
    "pop", "pop_0_2", "pop_3_5", "pop_6_10", "pop_11_17",
    "pop_18_24", "pop_25_39", "pop_40_54", "pop_55_64",
    "pop_65_79", "pop_80_plus", "pop_foreign", "pop_immigrant",
    "pop_women", "pop_men",
)

_SELECT = """
    SELECT iris_code, com_code, iris_name, dep_code, reg_code, year,
           pop, pop_0_2, pop_3_5, pop_6_10, pop_11_17,
           pop_18_24, pop_25_39, pop_40_54, pop_55_64,
           pop_65_79, pop_80_plus, pop_foreign, pop_immigrant,
           pop_women, pop_men
    FROM iris_population
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


class IrisPopulationService:

    @lru_cache(maxsize=1)
    def get_available_years(self) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT DISTINCT year FROM iris_population ORDER BY year")
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
                "total_pop":  sum((r["pop"] or 0) for r in iris_list) or None,
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
                SELECT ip.iris_code, ip.com_code, ip.iris_name, ip.dep_code, ip.reg_code, ip.year,
                       ip.pop, ip.pop_0_2, ip.pop_3_5, ip.pop_6_10, ip.pop_11_17,
                       ip.pop_18_24, ip.pop_25_39, ip.pop_40_54, ip.pop_55_64,
                       ip.pop_65_79, ip.pop_80_plus, ip.pop_foreign, ip.pop_immigrant,
                       ip.pop_women, ip.pop_men
                FROM iris_population ip
                JOIN geo_codes gc ON gc.codgeo = ip.com_code
                WHERE gc.epci = :epci_code AND ip.year = :year
                ORDER BY ip.com_code, ip.iris_code
            """)
            rows = db.execute(sql, {"epci_code": epci_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {
                "epci_code":  epci_code,
                "year":       resolved_year,
                "total_iris": len(iris_list),
                "total_pop":  sum((r["pop"] or 0) for r in iris_list) or None,
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
                "total_pop":  sum((r["pop"] or 0) for r in iris_list) or None,
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
                "total_pop":  sum((r["pop"] or 0) for r in iris_list) or None,
                "iris_list":  iris_list,
            }
        finally:
            db.close()
