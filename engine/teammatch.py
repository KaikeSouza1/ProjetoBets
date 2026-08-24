"""Resolve o mesmo time entre API-Football e football-data.org, que usam nomes/IDs diferentes.

Ex.: API-Football diz "Palmeiras"; football-data.org diz "SE Palmeiras".
Qualquer fonte pode "descobrir" um time primeiro — o merge por nome funciona nos dois sentidos.
"""
import re
import unicodedata

_NOISE_TOKENS = {
    "fc", "sc", "ec", "se", "ca", "cr", "ac", "af", "cd", "afc", "cfc",
    "fbc", "fbpa", "esporte", "clube", "futebol", "clube de regatas",
    "atletico", "athletic", "association", "club", "deportivo",
}


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t not in _NOISE_TOKENS]
    return " ".join(tokens).strip()


def _names_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    # "rayo vallecano" vs "rayo vallecano de madrid", "alaves" vs "deportivo alaves" (já sem o ruído)
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= 4 and shorter in longer


def find_matching_team_id(cur, name: str, id_column: str) -> int | None:
    target = normalize(name)
    if not target:
        return None
    cur.execute(f"SELECT id, name FROM teams WHERE {id_column} IS NULL")
    for team_id, existing_name in cur.fetchall():
        if _names_match(normalize(existing_name), target):
            return team_id
    return None


def upsert_team(cur, source: str, external_id: int, name: str, logo_url: str | None = None) -> int:
    """Vincula/cria o time em `teams`, fazendo merge por nome quando a outra fonte já o criou."""
    id_column = "api_football_id" if source == "api-football" else "football_data_id"

    cur.execute(f"SELECT id FROM teams WHERE {id_column} = %s", (external_id,))
    row = cur.fetchone()
    if row:
        return row[0]

    existing_id = find_matching_team_id(cur, name, id_column)
    if existing_id:
        cur.execute(f"UPDATE teams SET {id_column} = %s WHERE id = %s", (external_id, existing_id))
        return existing_id

    cur.execute(
        f"""INSERT INTO teams ({id_column}, name, logo_url) VALUES (%s, %s, %s) RETURNING id""",
        (external_id, name, logo_url),
    )
    return cur.fetchone()[0]
