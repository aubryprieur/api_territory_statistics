"""
app/services/iris_education_service.py
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_NUM_COLS = (
    "pop_2_5", "pop_6_10", "pop_11_14", "pop_15_17", "pop_18_24", "pop_25_29", "pop_30p",
    "scol_2_5", "scol_6_10", "scol_11_14", "scol_15_17", "scol_18_24", "scol_25_29", "scol_30p",
    "nscol_15p", "nscol_15p_no_dip", "nscol_15p_bepc", "nscol_15p_capbep",
    "nscol_15p_bac", "nscol_15p_sup2", "nscol_15p_sup34", "nscol_15p_sup5",
    "nscol_15p_men", "nscol_15p_men_no_dip", "nscol_15p_men_bepc", "nscol_15p_men_capbep",
    "nscol_15p_men_bac", "nscol_15p_men_sup2", "nscol_15p_men_sup34", "nscol_15p_men_sup5",
    "nscol_15p_women", "nscol_15p_women_no_dip", "nscol_15p_women_bepc", "nscol_15p_women_capbep",
    "nscol_15p_women_bac", "nscol_15p_women_sup2", "nscol_15p_women_sup34", "nscol_15p_women_sup5",
)

_SELECT = """
    SELECT iris_code, com_code, iris_name, dep_code, reg_code, year,
           pop_2_5, pop_6_10, pop_11_14, pop_15_17, pop_18_24, pop_25_29, pop_30p,
           scol_2_5, scol_6_10, scol_11_14, scol_15_17, scol_18_24, scol_25_29, scol_30p,
           nscol_15p, nscol_15p_no_dip, nscol_15p_bepc, nscol_15p_capbep,
           nscol_15p_bac, nscol_15p_sup2, nscol_15p_sup34, nscol_15p_sup5,
           nscol_15p_men, nscol_15p_men_no_dip, nscol_15p_men_bepc, nscol_15p_men_capbep,
           nscol_15p_men_bac, nscol_15p_men_sup2, nscol_15p_men_sup34, nscol_15p_men_sup5,
           nscol_15p_women, nscol_15p_women_no_dip, nscol_15p_women_bepc, nscol_15p_women_capbep,
           nscol_15p_women_bac, nscol_15p_women_sup2, nscol_15p_women_sup34, nscol_15p_women_sup5
    FROM iris_education
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


class IrisEducationService:

    @lru_cache(maxsize=1)
    def get_available_years(self) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT DISTINCT year FROM iris_education ORDER BY year")
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            db.close()

    def get_latest_year(self) -> Optional[int]:
        years = self.get_available_years()
        return max(years) if years else None

    def _resolve_year(self, year: Optional[int]) -> Optional[int]:
        return year if year is not None else self.get_latest_year()

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

    @lru_cache(maxsize=512)
    def get_by_epci(self, epci_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text("""
                SELECT ie.iris_code, ie.com_code, ie.iris_name, ie.dep_code, ie.reg_code, ie.year,
                       ie.pop_2_5, ie.pop_6_10, ie.pop_11_14, ie.pop_15_17, ie.pop_18_24, ie.pop_25_29, ie.pop_30p,
                       ie.scol_2_5, ie.scol_6_10, ie.scol_11_14, ie.scol_15_17, ie.scol_18_24, ie.scol_25_29, ie.scol_30p,
                       ie.nscol_15p, ie.nscol_15p_no_dip, ie.nscol_15p_bepc, ie.nscol_15p_capbep,
                       ie.nscol_15p_bac, ie.nscol_15p_sup2, ie.nscol_15p_sup34, ie.nscol_15p_sup5,
                       ie.nscol_15p_men, ie.nscol_15p_men_no_dip, ie.nscol_15p_men_bepc, ie.nscol_15p_men_capbep,
                       ie.nscol_15p_men_bac, ie.nscol_15p_men_sup2, ie.nscol_15p_men_sup34, ie.nscol_15p_men_sup5,
                       ie.nscol_15p_women, ie.nscol_15p_women_no_dip, ie.nscol_15p_women_bepc, ie.nscol_15p_women_capbep,
                       ie.nscol_15p_women_bac, ie.nscol_15p_women_sup2, ie.nscol_15p_women_sup34, ie.nscol_15p_women_sup5
                FROM iris_education ie
                JOIN geo_codes gc ON gc.codgeo = ie.com_code
                WHERE gc.epci = :epci_code AND ie.year = :year
                ORDER BY ie.com_code, ie.iris_code
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
