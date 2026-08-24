import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import db

if __name__ == "__main__":
    db.bootstrap()
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
    conn.close()
    print(f"Banco '{db.config.DB_NAME}' pronto. {len(tables)} tabelas:")
    for t in tables:
        print(" -", t)
