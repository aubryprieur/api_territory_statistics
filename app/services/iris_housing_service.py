"""
app/services/iris_housing_service.py
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_NUM_COLS = (
    "housing_total", "main_res", "second_res", "vacant", "houses", "apartments",
    "rp_1room", "rp_2rooms", "rp_3rooms", "rp_4rooms", "rp_5p_rooms",
    "rp_u30m2", "rp_30_40m2", "rp_40_60m2", "rp_60_80m2",
    "rp_80_100m2", "rp_100_120m2", "rp_120p_m2",
    "rp_built_pre1919", "rp_built_1919_1945", "rp_built_1946_1970",
    "rp_built_1971_1990", "rp_built_1991_2005", "rp_built_2006_2019",
    "households", "hh_moved_u2y", "hh_moved_2_4y", "hh_moved_5_9y", "hh_moved_10py",
    "rp_owners", "rp_renters", "rp_social_housing", "rp_free",
    "heat_gas_network", "heat_fuel", "heat_electric", "heat_gas_bottle", "heat_other",
    "hh_1p_car", "hh_1_car", "hh_2p_cars",
    "rp_standard_occ", "rp_mild_underuse", "rp_heavy_underuse",
    "rp_extreme_underuse", "rp_mild_overuse", "rp_heavy_overuse",
)

_SELECT = """
    SELECT iris_code, com_code, iris_name, dep_code, reg_code, year,
           housing_total, main_res, second_res, vacant, houses, apartments,
           rp_1room, rp_2rooms, rp_3rooms, rp_4rooms, rp_5p_rooms,
           rp_u30m2, rp_30_40m2, rp_40_60m2, rp_60_80m2,
           rp_80_100m2, rp_100_120m2, rp_120p_m2,
           rp_built_pre1919, rp_built_1919_1945, rp_built_1946_1970,
           rp_built_1971_1990, rp_built_1991_2005, rp_built_2006_2019,
           households, hh_moved_u2y, hh_moved_2_4y, hh_moved_5_9y, hh_moved_10py,
           rp_owners, rp_renters, rp_social_housing, rp_free,
           heat_gas_network, heat_fuel, heat_electric, heat_gas_bottle, heat_other,
           hh_1p_car, hh_1_car, hh_2p_cars,
           rp_standard_occ, rp_mild_underuse, rp_heavy_underuse,
           rp_extreme_underuse, rp_mild_overuse, rp_heavy_overuse
    FROM iris_housing
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


class IrisHousingService:

    @lru_cache(maxsize=1)
    def get_available_years(self) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("SELECT DISTINCT year FROM iris_housing ORDER BY year")
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
                SELECT ih.iris_code, ih.com_code, ih.iris_name, ih.dep_code, ih.reg_code, ih.year,
                       ih.housing_total, ih.main_res, ih.second_res, ih.vacant, ih.houses, ih.apartments,
                       ih.rp_1room, ih.rp_2rooms, ih.rp_3rooms, ih.rp_4rooms, ih.rp_5p_rooms,
                       ih.rp_u30m2, ih.rp_30_40m2, ih.rp_40_60m2, ih.rp_60_80m2,
                       ih.rp_80_100m2, ih.rp_100_120m2, ih.rp_120p_m2,
                       ih.rp_built_pre1919, ih.rp_built_1919_1945, ih.rp_built_1946_1970,
                       ih.rp_built_1971_1990, ih.rp_built_1991_2005, ih.rp_built_2006_2019,
                       ih.households, ih.hh_moved_u2y, ih.hh_moved_2_4y, ih.hh_moved_5_9y, ih.hh_moved_10py,
                       ih.rp_owners, ih.rp_renters, ih.rp_social_housing, ih.rp_free,
                       ih.heat_gas_network, ih.heat_fuel, ih.heat_electric, ih.heat_gas_bottle, ih.heat_other,
                       ih.hh_1p_car, ih.hh_1_car, ih.hh_2p_cars,
                       ih.rp_standard_occ, ih.rp_mild_underuse, ih.rp_heavy_underuse,
                       ih.rp_extreme_underuse, ih.rp_mild_overuse, ih.rp_heavy_overuse
                FROM iris_housing ih
                JOIN geo_codes gc ON gc.codgeo = ih.com_code
                WHERE gc.epci = :epci_code AND ih.year = :year
                ORDER BY ih.com_code, ih.iris_code
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
