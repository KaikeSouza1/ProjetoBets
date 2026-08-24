"""Nomes populares (curados manualmente) pros times do Brasileirão que só foram
resolvidos via football-data.org, que usa a razão social abreviada ('CA Paranaense',
'SE Palmeiras') em vez do nome fantasia. Busca automática pela API-Football foi tentada
e descartada (script `resolve_team_display_names.py`) — deu resultado ambíguo/errado
pra times conhecidos (ex.: 'CA Mineiro' bateu com 'América Mineiro', mas CA = Clube
Atlético → é Atlético Mineiro, time diferente). Nomes abaixo são conhecimento geral de
futebol brasileiro, não inventados nem adivinhados por heurística de string.

Só troca a coluna `name` (exibição) — não toca api_football_id nem nenhuma referência,
puramente cosmético."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import db

RENAMES = {
    25: "Botafogo",
    7: "Atlético Mineiro",
    12: "Athletico Paranaense",
    17: "Chapecoense",
    9: "Coritiba",
    24: "Vasco da Gama",
    20: "Bahia",
    13: "Vitória",
    16: "Grêmio",
    23: "Mirassol",
    18: "Santos",
    21: "São Paulo",
    19: "Corinthians",
    8: "Palmeiras",
}

if __name__ == "__main__":
    db.bootstrap()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            for team_id, new_name in RENAMES.items():
                cur.execute("SELECT name FROM teams WHERE id = %s", (team_id,))
                row = cur.fetchone()
                if not row:
                    print(f"[rename] id {team_id} não encontrado — pulando")
                    continue
                cur.execute("UPDATE teams SET name = %s WHERE id = %s", (new_name, team_id))
                print(f"[rename] {row[0]!r} -> {new_name!r}")
        conn.commit()
    finally:
        conn.close()
