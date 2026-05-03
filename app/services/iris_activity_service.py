"""
app/services/iris_activity_service.py
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_NUM_COLS = (
    "pop_15_64", "pop_15_24", "pop_25_54", "pop_55_64",
    "pop_men_15_64", "pop_men_15_24", "pop_men_25_54", "pop_men_55_64",
    "pop_women_15_64", "pop_women_15_24", "pop_women_25_54", "pop_women_55_64",
    "active_15_64", "active_15_24", "active_25_54", "active_55_64",
    "active_men_15_64", "active_men_15_24", "active_men_25_54", "active_men_55_64",
    "active_women_15_64", "active_women_15_24", "active_women_25_54", "active_women_55_64",
    "employed_15_64", "employed_15_24", "employed_25_54", "employed_55_64",
    "employed_men_15_64", "employed_men_15_24", "employed_men_25_54", "employed_men_55_64",
    "employed_women_15_64", "employed_women_15_24", "employed_women_25_54", "employed_women_55_64",
    "unemp_15_64", "unemp_15_24", "unemp_25_54", "unemp_55_64",
    "active_no_dip", "active_bepc", "active_capbep", "active_bac",
    "active_sup2", "active_sup34", "active_sup5",
    "unemp_no_dip", "unemp_bepc", "unemp_capbep", "unemp_bac",
    "unemp_sup2", "unemp_sup34", "unemp_sup5",
    "inactive_15_64", "inactive_men_15_64", "inactive_women_15_64",
    "student_15_64", "student_men_15_64", "student_women_15_64",
    "retired_15_64", "retired_men_15_64", "retired_women_15_64",
    "other_inactive_15_64", "other_inactive_men_15_64", "other_inactive_women_15_64",
    "act_farmers", "act_craftsmen", "act_executives", "act_intermediary", "act_employees", "act_workers",
    "emp_farmers", "emp_craftsmen", "emp_executives", "emp_intermediary", "emp_employees", "emp_workers",
    "employed_15p", "employed_men_15p", "employed_women_15p",
    "salaried_15p", "salaried_men_15p", "salaried_women_15p",
    "self_emp_15p", "self_emp_men_15p", "self_emp_women_15p",
    "employed_15p_pt", "salaried_15p_pt", "salaried_men_pt", "salaried_women_pt", "self_emp_15p_pt",
    "sal_cdi", "sal_cdd", "sal_interim", "sal_aided", "sal_appr",
    "self_emp_indep", "self_emp_employ", "self_emp_family",
    "work_same_commune", "work_other_commune", "work_other_dep_same_reg",
    "work_other_reg_metro", "work_other_reg_domtom",
    "transport_none", "transport_walk", "transport_bike",
    "transport_moto", "transport_car", "transport_transit",
)

_COLS_SQL = ", ".join(_NUM_COLS)

_SELECT = f"""
    SELECT iris_code, com_code, iris_name, dep_code, reg_code, year, {_COLS_SQL}
    FROM iris_activity
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


class IrisActivityService:

    @lru_cache(maxsize=1)
    def get_available_years(self) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT DISTINCT year FROM iris_activity ORDER BY year")
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
            return {"com_code": com_code, "year": resolved_year,
                    "total_iris": len(iris_list), "iris_list": iris_list}
        finally:
            db.close()

    @lru_cache(maxsize=512)
    def get_by_epci(self, epci_code: str, year: Optional[int] = None) -> dict:
        resolved_year = self._resolve_year(year)
        db = SessionLocal()
        try:
            sql = text(f"""
                SELECT ia.iris_code, ia.com_code, ia.iris_name, ia.dep_code, ia.reg_code, ia.year,
                       {', '.join(f'ia.{c}' for c in _NUM_COLS)}
                FROM iris_activity ia
                JOIN geo_codes gc ON gc.codgeo = ia.com_code
                WHERE gc.epci = :epci_code AND ia.year = :year
                ORDER BY ia.com_code, ia.iris_code
            """)
            rows = db.execute(sql, {"epci_code": epci_code, "year": resolved_year}).fetchall()
            iris_list = [_row_to_dict(r) for r in rows]
            return {"epci_code": epci_code, "year": resolved_year,
                    "total_iris": len(iris_list), "iris_list": iris_list}
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
            return {"dep_code": dep_code, "year": resolved_year,
                    "total_iris": len(iris_list), "iris_list": iris_list}
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
            return {"reg_code": reg_code, "year": resolved_year,
                    "total_iris": len(iris_list), "iris_list": iris_list}
        finally:
            db.close()
