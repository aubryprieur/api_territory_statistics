"""
Emploi et activité — INSEE, recensement (DS_RP_EMPLOI_LR/LT_PRINC/COMP, DS_RP_NAVETTES_PRINC),
table employment_by_territory. Millésimes 2012, 2017, 2023 ; valeurs officielles par territoire.

Indicateurs pour l'analyse des besoins sociaux :
  - activité, emploi, chômage (au sens du recensement) par âge et sexe ; écarts femmes-hommes
  - inactivité : étudiants, retraités, personnes au foyer, autres inactifs
  - chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle
  - emploi local : indicateur de concentration d'emploi, secteurs, salariat, temps partiel
  - mobilité domicile-travail : lieu de travail et mode de transport
  - conditions d'emploi des habitants (DS_RP_ACTIVITE_PRINC) : non-salariat, contrats à durée
    limitée (CDD, intérim, emplois aidés, apprentissage, stage), temps partiel par sexe et âge
"""
from app.models import EmploymentByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

AGES = ["15_64", "15_24", "25_54", "55_64"]
SEXES = ["", "_men", "_women"]
INACTIVE = ["retired", "students", "homemakers", "other_inactive"]
DIPLOMAS = ["no_diploma", "bepc", "cap_bep", "bac", "bac2", "bac3_4", "bac5_plus"]
PCS = {"1": "Agriculteurs exploitants", "2": "Artisans, commerçants, chefs d'entreprise",
       "3": "Cadres et professions intellectuelles supérieures", "4": "Professions intermédiaires",
       "5": "Employés", "6": "Ouvriers"}
SECTORS = {"agriculture": "Agriculture", "industry": "Industrie", "construction": "Construction",
           "trade_services": "Commerce, transports, services divers",
           "public_services": "Administration publique, enseignement, santé, action sociale"}
WORK_AREAS = ["in_commune", "other_commune_dep", "other_dep_region", "other_region", "abroad_overseas"]
COMMUTES = ["none", "walk", "bike", "two_wheels", "car", "public"]
RES_FIELDS = ["res_workers", "res_salaried", "res_non_salaried", "res_permanent", "res_fixed_term",
              "res_part_time", "res_salaried_part_time"]

COUNT_FIELDS = (
    [f"{p}_{a}{s}" for a in AGES for s in SEXES for p in ("pop", "active", "employed", "unemployed")]
    + [f"{p}_15_64{s}" for s in SEXES for p in INACTIVE]
    + ["employed_15_plus"]
    + [f"{p}_{d}" for d in DIPLOMAS for p in ("active", "unemployed")]
    + [f"{p}_pcs_{c}" for c in PCS for p in ("active", "employed")]
    + ["jobs", "jobs_salaried", "jobs_non_salaried", "jobs_salaried_part_time", "jobs_women"]
    + [f"jobs_{k}" for k in SECTORS]
    + ["workers"] + [f"work_{w}" for w in WORK_AREAS] + [f"commute_{c}" for c in COMMUTES]
    + [f"{f}{s}" for f in RES_FIELDS for s in SEXES]
    + [f"res_{p}_{a}{s}" for a in AGES for s in SEXES for p in ("salaried", "salaried_part_time")]
)


def _diff(a, b):
    return round(a - b, 2) if a is not None and b is not None else None


class EmploymentActivityService(TerritoryStatsService):
    MODEL = EmploymentByTerritory
    DATA_KEY = "employment_data"
    LABEL = "emploi et activité"
    EXTRA = {"labels": {"pcs": PCS, "sectors": SECTORS}}
    EVOLUTION_METRICS = (
        [f"{r}_{a}{s}" for r in ("activity_rate", "employment_rate", "unemployment_rate") for a in AGES for s in SEXES]
        + ["employment_gap_women_men", "activity_gap_women_men"]
        + [f"{p}_rate_15_64{s}" for p in INACTIVE for s in SEXES]
        + [f"pcs_{c}_active_percentage" for c in PCS] + [f"unemployment_rate_pcs_{c}" for c in PCS]
        + ["jobs", "employment_concentration", "salaried_percentage", "part_time_salaried_percentage",
           "women_jobs_percentage"]
        + [f"jobs_{k}_percentage" for k in SECTORS]
        + [f"work_{w}_percentage" for w in WORK_AREAS] + [f"commute_{c}_percentage" for c in COMMUTES]
        + ["unemployed_15_64", "unemployed_15_24"]
        + [f"{r}{s}" for r in ("fixed_term_percentage", "non_salaried_percentage", "part_time_percentage",
                                "salaried_part_time_percentage") for s in SEXES]
        + [f"salaried_part_time_percentage_{a}{s}" for a in AGES for s in SEXES]
        + ["part_time_gap_women_men", "fixed_term_gap_women_men"]
    )

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in COUNT_FIELDS}
        d = dict(c)

        # --- Activité, emploi, chômage par âge et sexe
        for a in AGES:
            for s in SEXES:
                pop, active = c[f"pop_{a}{s}"], c[f"active_{a}{s}"]
                d[f"activity_rate_{a}{s}"] = pct(active, pop)            # actifs / population
                d[f"employment_rate_{a}{s}"] = pct(c[f"employed_{a}{s}"], pop)  # actifs occupés / population
                d[f"unemployment_rate_{a}{s}"] = pct(c[f"unemployed_{a}{s}"], active)  # chômeurs / actifs
                d[f"inactive_{a}{s}"] = (pop - active) if pop is not None and active is not None else None
        d["employment_gap_women_men"] = _diff(d["employment_rate_15_64_women"], d["employment_rate_15_64_men"])
        d["activity_gap_women_men"] = _diff(d["activity_rate_15_64_women"], d["activity_rate_15_64_men"])

        # --- Inactivité (% de la population 15-64 ans du même sexe)
        for s in SEXES:
            for p in INACTIVE:
                d[f"{p}_rate_15_64{s}"] = pct(c[f"{p}_15_64{s}"], c[f"pop_15_64{s}"])
            d[f"inactivity_rate_15_64{s}"] = pct(d[f"inactive_15_64{s}"], c[f"pop_15_64{s}"])
            # chômeurs en % de la population (pour décomposer la population 15-64 ans à 100 %)
            d[f"unemployed_pop_rate_15_64{s}"] = pct(c[f"unemployed_15_64{s}"], c[f"pop_15_64{s}"])

        # --- Chômage selon le diplôme (2023)
        for dip in DIPLOMAS:
            d[f"unemployment_rate_{dip}"] = pct(c[f"unemployed_{dip}"], c[f"active_{dip}"])
        low_act = total(c["active_no_diploma"], c["active_bepc"])
        low_unemp = total(c["unemployed_no_diploma"], c["unemployed_bepc"])
        d["unemployment_rate_low_qualified"] = pct(low_unemp, low_act)
        hi_act = total(c["active_bac2"], c["active_bac3_4"], c["active_bac5_plus"])
        hi_unemp = total(c["unemployed_bac2"], c["unemployed_bac3_4"], c["unemployed_bac5_plus"])
        d["unemployment_rate_higher_education"] = pct(hi_unemp, hi_act)

        # --- Catégories socioprofessionnelles des actifs 15-64 ans
        active_pcs_total = total(*(c[f"active_pcs_{p}"] for p in PCS))
        for p in PCS:
            d[f"pcs_{p}_active_percentage"] = pct(c[f"active_pcs_{p}"], active_pcs_total)
            a_, e_ = c[f"active_pcs_{p}"], c[f"employed_pcs_{p}"]
            d[f"unemployment_rate_pcs_{p}"] = pct(a_ - e_, a_) if a_ is not None and e_ is not None else None

        # --- Emploi au lieu de travail
        jobs = c["jobs"]
        d["employment_concentration"] = pct(jobs, c["employed_15_plus"])  # emplois pour 100 actifs occupés résidents
        d["salaried_percentage"] = pct(c["jobs_salaried"], jobs)
        d["part_time_salaried_percentage"] = pct(c["jobs_salaried_part_time"], c["jobs_salaried"])
        d["women_jobs_percentage"] = pct(c["jobs_women"], jobs)
        sectors_total = total(*(c[f"jobs_{k}"] for k in SECTORS))
        for k in SECTORS:
            d[f"jobs_{k}_percentage"] = pct(c[f"jobs_{k}"], sectors_total)

        # --- Navettes domicile-travail (% des actifs occupés de 15 ans ou plus)
        for w in WORK_AREAS:
            d[f"work_{w}_percentage"] = pct(c[f"work_{w}"], c["workers"])
        d["work_outside_commune_percentage"] = pct(
            total(*(c[f"work_{w}"] for w in WORK_AREAS if w != "in_commune")), c["workers"])
        commute_total = total(*(c[f"commute_{m}"] for m in ["none", "walk", "two_wheels", "car", "public"]))
        for m in COMMUTES:
            d[f"commute_{m}_percentage"] = pct(c[f"commute_{m}"], commute_total)

        # --- Conditions d'emploi des habitants (actifs occupés de 15 ans ou plus, au lieu de résidence)
        for s in SEXES:
            d[f"fixed_term_percentage{s}"] = pct(c[f"res_fixed_term{s}"], c[f"res_salaried{s}"])  # % des salariés
            d[f"permanent_percentage{s}"] = pct(c[f"res_permanent{s}"], c[f"res_salaried{s}"])
            d[f"non_salaried_percentage{s}"] = pct(c[f"res_non_salaried{s}"], c[f"res_workers{s}"])
            d[f"part_time_percentage{s}"] = pct(c[f"res_part_time{s}"], c[f"res_workers{s}"])
            d[f"salaried_part_time_percentage{s}"] = pct(c[f"res_salaried_part_time{s}"], c[f"res_salaried{s}"])
            for a in AGES:
                d[f"salaried_part_time_percentage_{a}{s}"] = pct(c[f"res_salaried_part_time_{a}{s}"],
                                                                 c[f"res_salaried_{a}{s}"])
        d["part_time_gap_women_men"] = _diff(d["salaried_part_time_percentage_women"],
                                             d["salaried_part_time_percentage_men"])
        d["fixed_term_gap_women_men"] = _diff(d["fixed_term_percentage_women"], d["fixed_term_percentage_men"])
        return d
