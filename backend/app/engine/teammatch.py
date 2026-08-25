"""Normalização central de nome de time — usada por QUALQUER fonte que precise casar
time por nome (API-Football, football-data.org, odds-api.io). Antes desta consolidação,
`multi_bookmaker_odds.py` mantinha sua PRÓPRIA cópia de lista de ruído + match (achado
na auditoria de 25/08/2026) — já tinha divergido da lista daqui (faltava sufixo de
estado como "SP"/"RJ" aqui, faltava "athletic"/"deportivo" lá), risco real de um dia
combinar errado dependendo de qual cópia rodasse. Uma lista, um critério de match, só.

Ex.: API-Football diz "Palmeiras"; football-data.org diz "SE Palmeiras"; odds-api.io
diz "SE Palmeiras SP". Qualquer fonte pode "descobrir" um time primeiro — o merge por
nome funciona nos dois sentidos.
"""
import re
import unicodedata

_NOISE_TOKENS = {
    # prefixo/sufixo de organização (várias fontes, várias línguas)
    "fc", "sc", "ec", "se", "ca", "cr", "ac", "af", "cd", "afc", "cfc", "aa", "rb", "ge", "ar",
    "fbc", "fbpa", "esporte", "esportes", "clube", "clube de regatas", "futebol", "de", "do",
    "atletico", "athletic", "association", "club", "deportivo",
    # sufixo de estado brasileiro (odds-api.io usa, ex.: "SE Palmeiras SP")
    "sp", "rj", "mg", "rs", "pr", "pe", "go", "df", "es", "pi", "al", "ma", "pa", "am", "rn", "pb", "to", "ba", "sc",
}


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t not in _NOISE_TOKENS]
    return " ".join(tokens).strip()


def names_match(a: str, b: str) -> bool:
    """Espera nome JÁ normalizado nos dois lados (chame `normalize` antes) — evita
    normalizar 2x sem querer e mascarar um bug de token."""
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
        if names_match(normalize(existing_name), target):
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
