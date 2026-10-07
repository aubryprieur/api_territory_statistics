"""
Base commune des services « *_by_territory » (valeurs officielles INSEE par territoire).

Chaque table a la même clé (geo_level, geo_code, year) avec geo_level ∈ COM, ARM, EPCI,
DEP, REG, FRANCE ('FM' = France métropolitaine). Un service concret définit :
  - MODEL            : le modèle SQLAlchemy
  - DATA_KEY         : la clé des données annuelles dans la réponse (ex. "education_data")
  - LABEL            : libellé pour les messages d'erreur (ex. "scolarisation et diplômes")
  - EVOLUTION_METRICS: les indicateurs dont on calcule l'évolution
  - year_data(row)   : effectifs + taux pour une ligne
"""
import math

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal

FRANCE_CODE = "FM"
MIN_EVOLUTION_GAP = 5  # années minimum entre millésime de comparaison et dernier millésime


def num(value):
    """float ou None (valeur absente / NaN)."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def pct(part, total):
    if part is None or not total:
        return None
    return round(part / total * 100, 2)


def total(*values):
    values = [v for v in values if v is not None]
    return sum(values) if values else None


class TerritoryStatsService:
    MODEL = None
    DATA_KEY = "data"
    LABEL = "données"
    EVOLUTION_METRICS = []
    EXTRA = {}  # métadonnées ajoutées à chaque réponse (libellés...)

    def year_data(self, row):
        raise NotImplementedError

    # ------------------------------------------------------------------ évolution
    def default_period(self, years):
        end = years[-1]
        earlier = [y for y in years if y <= end - MIN_EVOLUTION_GAP]
        return (earlier[-1] if earlier else years[0]), end

    def evolution(self, data, start_year=None, end_year=None):
        years = sorted(data)
        if len(years) < 2:
            return {}
        default_start, default_end = self.default_period(years)
        start_year = start_year or default_start
        end_year = end_year or default_end
        if start_year not in data or end_year not in data:
            return {"error": f"Millésimes disponibles : {', '.join(map(str, years))}"}
        result = {}
        for metric in self.EVOLUTION_METRICS:
            v0, v1 = data[start_year].get(metric), data[end_year].get(metric)
            if v0 is None or v1 is None:
                continue
            result[metric] = {
                "start_value": v0,
                "end_value": v1,
                "difference": round(v1 - v0, 2),  # en points pour les taux
                "evolution_percentage": round((v1 - v0) / v0 * 100, 2) if v0 else 0.0,
                "period": f"{start_year}-{end_year}",
            }
        return result

    # --------------------------------------------------------------------- lecture
    def get(self, level, code, start_year=None, end_year=None):
        model = self.MODEL
        db = SessionLocal()
        try:
            rows = (
                db.query(model)
                .filter(model.geo_level == level, model.geo_code == str(code))
                .order_by(model.year)
                .all()
            )
            if not rows:
                return {"error": f"Aucune donnée {self.LABEL} pour {level} {code}"}
            data = {row.year: self.year_data(row) for row in rows}
            start, end = self.default_period(sorted(data))
            return {
                "territory": {"level": level, "code": str(code)},
                "available_years": sorted(data),
                "latest_year": end,
                "comparison_year": start,
                **self.EXTRA,
                self.DATA_KEY: data,
                "evolution": self.evolution(data, start_year, end_year),
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def by_commune(self, code, start_year=None, end_year=None):
        code = str(code).zfill(5)
        result = self.get("COM", code, start_year, end_year)
        if "error" in result:
            arm = self.get("ARM", code, start_year, end_year)  # arrondissements Paris/Lyon/Marseille
            if "error" not in arm:
                return arm
        return result

    def by_epci(self, code, start_year=None, end_year=None):
        return self.get("EPCI", code, start_year, end_year)

    def by_department(self, code, start_year=None, end_year=None):
        code = str(code)
        if code.isdigit() and len(code) < 2:
            code = code.zfill(2)
        return self.get("DEP", code, start_year, end_year)

    def by_region(self, code, start_year=None, end_year=None):
        return self.get("REG", str(code).zfill(2), start_year, end_year)

    def france(self, start_year=None, end_year=None):
        """France métropolitaine."""
        return self.get("FRANCE", FRANCE_CODE, start_year, end_year)
