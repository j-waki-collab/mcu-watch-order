"""相関図に使う俳優の顔写真をTMDBから取ってきて people.js を作るスクリプト。

fetch_posters.py と同じトークンを使います。単体で動かすときは
環境変数 TMDB_TOKEN を設定してください。
"""
import json, os, re, sys, time
import requests

TOKEN = (os.environ.get("TMDB_TOKEN") or "").strip()
if not TOKEN:
    sys.exit("TMDB_TOKEN が設定されていません。")

HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, "chart.html"), encoding="utf-8").read()
# C配列の行から俳優名を拾う: ["id","キャラ名","俳優名",...]
ACTORS = []
for m in re.finditer(r'^\["[^"]+","[^"]+","([^"]+)"', html, re.M):
    if m.group(1) not in ACTORS:
        ACTORS.append(m.group(1))

S = requests.Session()
if re.fullmatch(r"[0-9a-f]{32}", TOKEN):
    S.params = {"api_key": TOKEN}
else:
    S.headers["Authorization"] = "Bearer " + TOKEN

check = S.get("https://api.themoviedb.org/3/configuration", timeout=15)
if check.status_code == 401:
    sys.exit("トークンが正しくないようです。TMDBの設定→APIの画面からコピーし直してください。")
check.raise_for_status()

people, report = {}, []
for name in ACTORS:
    r = S.get("https://api.themoviedb.org/3/search/person", params={"query": name}, timeout=15)
    r.raise_for_status()
    res = r.json().get("results", [])
    time.sleep(0.25)
    if res and res[0].get("profile_path"):
        people[name] = res[0]["profile_path"]
        report.append(f"OK   {name}  ->  {res[0]['name']}")
    else:
        report.append(f"なし {name}")

with open(os.path.join(HERE, "people.js"), "w", encoding="utf-8") as f:
    f.write("// fetch_people.py で自動生成\nwindow.PEOPLE=" + json.dumps(people, ensure_ascii=False, indent=1) + ";\n")

print("\n".join(report))
print(f"\n顔写真取得: {len(people)} / {len(ACTORS)} 人。people.js を更新しました。")
