import asyncio
import asyncpg

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "5456CopaS",
    "database": "myapi_db"
}

QUERIES = [
    "SELECT * FROM schooling WHERE year = 2021 AND geo_code = '59484';",
    "SELECT * FROM schooling WHERE year = 2021 AND geo_code = '245901160';",
    "SELECT * FROM schooling WHERE year = 2021 AND geo_code LIKE '59%';",
    "SELECT * FROM schooling WHERE year = 2021 AND geo_code LIKE '32%';",
    "SELECT * FROM schooling WHERE year = 2021;"
]

async def fetch_data(query):
    """Exécute une requête et mesure son temps"""
    conn = await asyncpg.connect(**DB_CONFIG)
    start_time = asyncio.get_event_loop().time()
    rows = await conn.fetch(query)
    elapsed_time = asyncio.get_event_loop().time() - start_time
    await conn.close()
    print(f"✅ {query[:50]}... → {len(rows)} résultats, temps: {elapsed_time:.3f} sec")

async def main():
    """Exécute toutes les requêtes en parallèle"""
    tasks = [fetch_data(q) for q in QUERIES]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
