"""Smoke test: confirm the league connection works. Run: python league_info.py"""

from yahoo_client import api_get, league_key

key = league_key()
print(f"League key: {key}\n")

league = api_get(f"league/{key}")["fantasy_content"]["league"][0]
print(f"Name:    {league.get('name')}")
print(f"Season:  {league.get('season')}")
print(f"Teams:   {league.get('num_teams')}")
print(f"Week:    {league.get('current_week')}")
print(f"URL:     {league.get('url')}\n")

teams = api_get(f"league/{key}/teams")["fantasy_content"]["league"][1]["teams"]
print("Teams:")
for i in range(int(teams["count"])):
    meta = teams[str(i)]["team"][0]
    name = next(d["name"] for d in meta if isinstance(d, dict) and "name" in d)
    print(f"  {i + 1:2}. {name}")
