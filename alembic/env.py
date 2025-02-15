from logging.config import fileConfig
import logging
from sqlalchemy import create_engine, pool
from alembic import context
from app.database import Base
from app.models import Birth, Family, GeoCode  # Ajoute tous les modèles

# Configuration du logger
fileConfig(context.config.config_file_name)
logger = logging.getLogger("alembic.runtime.migration")

# Vérifie si les modèles sont bien chargés
if not Base.metadata.tables:
    raise RuntimeError("❌ Aucune table détectée ! Vérifie tes imports dans env.py")

target_metadata = Base.metadata


def log_migration_step(step: str) -> None:
    """Log des étapes des migrations"""
    logger.info(f"🔄 Exécution de la migration : {step}")


def run_migrations_offline() -> None:
    """Exécution des migrations en mode 'offline'."""
    log_migration_step("Mode offline détecté")

    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

    log_migration_step("Migrations exécutées avec succès ✅")


def run_migrations_online() -> None:
    """Exécution des migrations en mode 'online'."""
    log_migration_step("Mode online détecté")

    DATABASE_URL = context.config.get_main_option("sqlalchemy.url")
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    log_migration_step("Migrations exécutées avec succès ✅")


# Détermine si l'exécution est en mode online ou offline
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
