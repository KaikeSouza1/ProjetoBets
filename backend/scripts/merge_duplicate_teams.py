"""Reconciliação única: acha times duplicados (um só com api_football_id, outro só com
football_data_id) que o matcher de nomes não uniu na hora certa, e funde em um só registro."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine import teammatch

REFERENCING_TABLES = [
    ("fixtures", "home_team_id"), ("fixtures", "away_team_id"),
    ("fd_matches", "home_team_id"), ("fd_matches", "away_team_id"),
    ("standings_snapshots", "team_id"),
    ("team_recent_form", "team_id"),
    ("fixture_statistics", "team_id"),
    ("fixture_events", "team_id"),
    ("fixture_lineups", "team_id"),
    ("fixture_player_stats", "team_id"),
    ("injuries", "team_id"),
]


def run():
    conn = db.get_connection()
    merges = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, api_football_id, football_data_id FROM teams")
            teams = cur.fetchall()

            af_only = [(tid, name) for tid, name, af, fd in teams if af is not None and fd is None]
            fd_only = [(tid, name) for tid, name, af, fd in teams if fd is not None and af is None]

            for fd_id, fd_name in fd_only:
                fd_norm = teammatch.normalize(fd_name)
                match = next(
                    (af_id for af_id, af_name in af_only if teammatch.names_match(teammatch.normalize(af_name), fd_norm)),
                    None,
                )
                if match is None:
                    continue

                print(f"[merge] '{fd_name}' (id={fd_id}) -> '{dict(((i,n) for i,n in af_only))[match]}' (id={match})")
                cur.execute("SELECT football_data_id FROM teams WHERE id = %s", (fd_id,))
                fd_value = cur.fetchone()[0]
                for table, column in REFERENCING_TABLES:
                    cur.execute(f"UPDATE {table} SET {column} = %s WHERE {column} = %s", (match, fd_id))
                cur.execute("DELETE FROM teams WHERE id = %s", (fd_id,))
                cur.execute("UPDATE teams SET football_data_id = %s WHERE id = %s", (fd_value, match))
                merges += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[merge] {merges} times duplicados fundidos")


if __name__ == "__main__":
    run()
