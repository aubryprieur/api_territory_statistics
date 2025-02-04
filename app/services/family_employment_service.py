import pandas as pd
from pathlib import Path

class FamilyEmploymentService:
    def __init__(self):
        # Dictionnaire des libellés TF12
        self.tf12_labels = {
            11: "Famille monoparentale - Homme actif ayant un emploi",
            12: "Famille monoparentale - Homme sans emploi",
            21: "Famille monoparentale - Femme active ayant un emploi",
            22: "Famille monoparentale - Femme sans emploi",
            41: "Couple avec enfant(s) - Deux parents actifs ayant un emploi",
            42: "Couple avec enfant(s) - Homme actif ayant un emploi, conjoint sans emploi",
            43: "Couple avec enfant(s) - Femme active ayant un emploi, conjoint sans emploi",
            44: "Couple avec enfant(s) - Aucun parent actif ayant un emploi"
        }

        # Chargement du fichier de géographie
        try:
            self.geo_df = pd.read_csv(
                Path("data/geography/COG_au_01-01-2024.csv"),
                delimiter=";",
                encoding="utf-8",
                dtype={"CODGEO": str, "DEP": str, "REG": str, "EPCI": str},
                usecols=["CODGEO", "DEP", "REG", "EPCI", "LIBGEO"]
            )
        except Exception as e:
            print(f"Erreur lors du chargement des données géographiques: {str(e)}")
            self.geo_df = pd.DataFrame()

        # Charger les données pour chaque année
        self.dfs = {}
        for year in range(2021, 2022):  # Ajustez simplement cette plage pour ajouter des années
            try:
                self.dfs[year] = pd.read_csv(
                    Path(f"data/families/family_employment/TD_FAM6v2_{year}.csv"),
                    delimiter=";",
                    encoding="utf-8",
                    dtype={"CODGEO": str}
                )
                print(f"Données {year} chargées - Colonnes:", self.dfs[year].columns.tolist())
                print(f"Valeurs uniques TF12 pour {year}:", self.dfs[year]["TF12"].unique())
            except Exception as e:
                print(f"Erreur lors du chargement des données {year}: {str(e)}")
                self.dfs[year] = pd.DataFrame()

    def _calculate_distribution(self, data, age_group=0):
        """Calcule la répartition des TF12 pour AGEFOR5 spécifié (0 = moins de 3 ans, 3 = 3-5 ans)"""
        try:
            print(f"\nDonnées avant filtrage pour AGEFOR5 = {age_group}:")
            print("Nombre de lignes:", len(data))
            print("Valeurs uniques AGEFOR5:", data["AGEFOR5"].unique())
            print("Valeurs uniques TF12:", data["TF12"].unique())

            # Filtrer pour AGEFOR5 spécifié
            filtered_data = data[data["AGEFOR5"] == age_group]
            print(f"\nAprès filtrage AGEFOR5 = {age_group}:")
            print("Nombre de lignes filtrées:", len(filtered_data))

            # Calculer le total
            total = filtered_data["NB"].sum()
            print("Total NB:", total)

            # Calculer les pourcentages pour chaque TF12
            distributions = {}
            if total > 0:
                for tf12 in sorted(filtered_data["TF12"].unique()):
                    count = filtered_data[filtered_data["TF12"] == tf12]["NB"].sum()
                    percentage = (count / total * 100) if total > 0 else 0

                    key = self.tf12_labels.get(tf12, f"Type {tf12}")
                    distributions[key] = {
                        "code": str(tf12),
                        "count": float(count),
                        "percentage": round(float(percentage), 1)
                    }
                    print(f"TF12 {tf12} - {key}: count = {count}, percentage = {percentage}%")

            return {
                "total_count": float(total),
                "distributions": distributions,
                "age_group": "0-2 ans" if age_group == 0 else "3-5 ans"
            }
        except Exception as e:
            print(f"Erreur dans le calcul de la distribution: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "total_count": 0,
                "distributions": {},
                "age_group": "0-2 ans" if age_group == 0 else "3-5 ans"
            }

    def get_commune_distribution(self, code: str, age_group=0):
        """Récupère la distribution pour une commune"""
        try:
            print(f"\nRecherche pour la commune {code}")
            geo_info = self.geo_df[self.geo_df['CODGEO'] == str(code)]
            if geo_info.empty:
                print("Commune non trouvée dans le fichier COG")
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "data": {}
                }

            print("Commune trouvée dans COG:", geo_info.iloc[0].to_dict())
            results = {}
            for year in self.dfs:
                df_year = self.dfs[year]
                print(f"\nRecherche des données pour {year}")
                commune_data = df_year[df_year["CODGEO"] == str(code)]
                print(f"Nombre de lignes trouvées pour la commune: {len(commune_data)}")
                if not commune_data.empty:
                    print("Exemple de ligne:", commune_data.iloc[0].to_dict())
                results[year] = self._calculate_distribution(commune_data, age_group)

            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.iloc[0]['LIBGEO'],
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la commune {code}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "territory_type": "commune",
                "code": code,
                "name": "Erreur",
                "data": {}
            }

    def get_epci_distribution(self, epci: str, age_group=0):
        """Récupère la distribution pour un EPCI"""
        try:
            communes = self.geo_df[self.geo_df['EPCI'] == str(epci)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "epci",
                    "code": epci,
                    "name": "EPCI inconnu",
                    "data": {}
                }

            results = {}
            for year in self.dfs:
                df_year = self.dfs[year]
                epci_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_distribution(epci_data, age_group)

            return {
                "territory_type": "epci",
                "code": epci,
                "name": f"EPCI {epci}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour l'EPCI {epci}: {str(e)}")
            return {
                "territory_type": "epci",
                "code": epci,
                "name": "Erreur",
                "data": {}
            }

    def get_department_distribution(self, dep: str, age_group=0):
        """Récupère la distribution pour un département"""
        try:
            communes = self.geo_df[self.geo_df['DEP'] == str(dep)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "data": {}
                }

            results = {}
            for year in self.dfs:
                df_year = self.dfs[year]
                dep_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_distribution(dep_data, age_group)

            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour le département {dep}: {str(e)}")
            return {
                "territory_type": "department",
                "code": dep,
                "name": "Erreur",
                "data": {}
            }

    def get_region_distribution(self, reg: str, age_group=0):
        """Récupère la distribution pour une région"""
        try:
            communes = self.geo_df[self.geo_df['REG'] == str(reg)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "region",
                    "code": reg,
                    "name": "Région inconnue",
                    "data": {}
                }

            results = {}
            for year in self.dfs:
                df_year = self.dfs[year]
                reg_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_distribution(reg_data, age_group)

            return {
                "territory_type": "region",
                "code": reg,
                "name": f"Région {reg}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la région {reg}: {str(e)}")
            return {
                "territory_type": "region",
                "code": reg,
                "name": "Erreur",
                "data": {}
            }

    def get_france_distribution(self, age_group=0):
        """Récupère la distribution pour la France entière en agrégeant directement les données"""
        try:
            results = {}
            for year in self.dfs:
                # On utilise directement tout le dataframe sans filtrage géographique
                results[year] = self._calculate_distribution(self.dfs[year], age_group)

            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la France: {str(e)}")
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "data": {}
            }
