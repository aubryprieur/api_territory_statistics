-- =============================================================================
-- Script SQL pour ajouter les index de performance
-- Exécutez directement sur votre base PostgreSQL si vous ne voulez pas
-- passer par Alembic.
--
-- Temps estimé : quelques secondes à quelques minutes selon la taille des données
-- =============================================================================

-- Index sur geo_codes pour les filtres par territoire
CREATE INDEX IF NOT EXISTS ix_geo_codes_reg ON geo_codes(reg);
CREATE INDEX IF NOT EXISTS ix_geo_codes_dep ON geo_codes(dep);
CREATE INDEX IF NOT EXISTS ix_geo_codes_epci ON geo_codes(epci);

-- Index composite sur populations pour les JOIN + filtres par tranche d'âge
CREATE INDEX IF NOT EXISTS ix_populations_codgeo_aged100 ON populations(codgeo, aged100);

-- Index sur aged100 seul pour les requêtes France (agrégation totale filtrée par âge)
CREATE INDEX IF NOT EXISTS ix_populations_aged100 ON populations(aged100);

-- Vérification
SELECT indexname, tablename FROM pg_indexes
WHERE tablename IN ('geo_codes', 'populations')
ORDER BY tablename, indexname;
