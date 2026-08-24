"""Vários times brasileiros só foram resolvidos via football-data.org, que usa nome
formal/abreviado (razão social: 'CA Paranaense', 'CR Vasco da Gama', 'SE Palmeiras').
A API-Football tende a usar o nome popular ('Atletico Paranaense', 'Vasco da Gama',
'Palmeiras'). Este script busca cada time sem `api_football_id` na API-Football pelo
nome completo, filtra por país e exclui categorias óbvias (feminino/sub/reserva) e,
achando exatamente 1 correspondência, atualiza `api_football_id` e troca o nome de
exibição pelo da API-Football.

MODO DRY-RUN por padrão (só imprime) — rode com --apply pra gravar de verdade. Não
adivinha: time sem correspondência única fica de fora, listado pra revisão manual."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db
from app.engine.integrations import api_football

PACING_SECONDS = 7  # limite da API-Football é 10 req/min — 6s é o mínimo teórico, 7s dá folga

_NON_FIRST_TEAM_MARKERS = (" w", "women", "sub-", "sub 2", " ii", " b", "youth", "feminino")


def _is_first_team(name: str) -> bool:
    lowered = name.lower()
    return not any(lowered.endswith(m) or f"{m} " in lowered for m in _NON_FIRST_TEAM_MARKERS)


def _candidates(competition_code: str | None = None) -> list[tuple]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT t.id, t.name FROM teams t
                   JOIN fd_matches fm ON fm.home_team_id = t.id OR fm.away_team_id = t.id
                   WHERE t.api_football_id IS NULL AND t.football_data_id IS NOT NULL
                     AND (%s IS NULL OR fm.competition_code = %s)
                   ORDER BY t.name""",
                (competition_code, competition_code),
            )
            return cur.fetchall()
    finally:
        conn.close()


def _apply(team_id: int, api_football_id: int, new_name: str):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE teams SET api_football_id = %s, name = %s WHERE id = %s",
                (api_football_id, new_name, team_id),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    apply_changes = "--apply" in sys.argv
    db.bootstrap()
    unresolved = []
    resolved = 0

    for team_id, current_name in _candidates(competition_code="BSA"):
        try:
            results = api_football.get("teams", {"search": current_name})
        except Exception as exc:
            print(f"[resolve] busca falhou p/ '{current_name}': {exc}")
            unresolved.append((current_name, "erro de busca", []))
            time.sleep(PACING_SECONDS)
            continue

        candidates = [
            r["team"] for r in results
            if r["team"].get("country") == "Brazil" and _is_first_team(r["team"]["name"])
        ]

        if len(candidates) == 1:
            match = candidates[0]
            tag = "[APLICADO]" if apply_changes else "[dry-run — seria aplicado]"
            print(f"[resolve] {tag} '{current_name}' -> '{match['name']}' (api_football_id={match['id']})")
            if apply_changes:
                _apply(team_id, match["id"], match["name"])
            resolved += 1
        else:
            names = [f"{c['name']} (id={c['id']})" for c in candidates]
            print(f"[resolve] '{current_name}': {len(candidates)} candidatos -> {names}")
            unresolved.append((current_name, f"{len(candidates)} candidatos", names))

        time.sleep(PACING_SECONDS)

    print(f"\n[resolve] {resolved} times {'atualizados' if apply_changes else 'resolvidos (dry-run)'}")
    if unresolved:
        print("[resolve] precisam de revisão manual:")
        for name, reason, names in unresolved:
            print(f"  - {name}: {reason} {names}")
