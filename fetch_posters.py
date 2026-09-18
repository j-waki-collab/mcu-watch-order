"""TMDBからポスター画像の場所を取ってきて posters.js を作るスクリプト。

使い方:
  1. https://www.themoviedb.org でアカウントを作り、設定の「API」から
     「APIリードアクセストークン」を発行する
  2. 環境変数 TMDB_TOKEN にトークンを入れて実行する
       いちばん簡単なのは「ポスター取得.bat」をダブルクリックして貼り付ける方法
  3. 表示された「一致した作品名」が正しいか確認する
     間違っていたら OVERRIDES に検索語を足して再実行する
"""
import json, os, re, sys, time
import requests

TOKEN = os.environ.get("TMDB_TOKEN")
if not TOKEN:
    sys.exit("TMDB_TOKEN が設定されていません。ファイル先頭の使い方を見てください。")

HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
# D配列の行: ["章","邦題","原題","種類","公開年",...]
ROWS = re.findall(r'^\["[^"]+","([^"]+)","([^"]+)","(film|series|anim|tv)","(\d{4})"', html, re.M)

# 原題のままでは見つからない作品の検索条件: 原題 -> (movie/tv, 検索語, 年)
OVERRIDES = {
    "Agent Carter": ("tv", "Marvel's Agent Carter", 2015),
    "Agents of S.H.I.E.L.D.": ("tv", "Marvel's Agents of S.H.I.E.L.D.", 2013),
    "Daredevil / Jessica Jones": ("tv", "Marvel's Daredevil", 2015),
    "The Defenders Saga": ("tv", "Marvel's The Defenders", 2017),
    "Werewolf by Night": ("movie", "Werewolf by Night", 2022),
    "The Guardians of the Galaxy Holiday Special": ("movie", "The Guardians of the Galaxy Holiday Special", 2022),
    "What If...?": ("tv", "What If...?", 2021),
    "Loki": ("tv", "Loki", 2021),
}

S = requests.Session()
TOKEN = TOKEN.strip()
if re.fullmatch(r"[0-9a-f]{32}", TOKEN):
    # 短い「APIキー」を貼った場合
    S.params = {"api_key": TOKEN}
else:
    # 長い「APIリードアクセストークン」を貼った場合
    S.headers["Authorization"] = "Bearer " + TOKEN

check = S.get("https://api.themoviedb.org/3/configuration", timeout=15)
if check.status_code == 401:
    sys.exit("トークンが正しくないようです。TMDBの設定→APIの画面からコピーし直してください。")
check.raise_for_status()

def search(kind, query, year):
    params = {"query": query, "language": "ja-JP"}
    params["year" if kind == "movie" else "first_air_date_year"] = year
    r = S.get(f"https://api.themoviedb.org/3/search/{kind}", params=params, timeout=15)
    r.raise_for_status()
    res = r.json().get("results", [])
    if not res:  # 年がずれている場合に備えて年なしで再検索
        params.pop("year", None); params.pop("first_air_date_year", None)
        res = S.get(f"https://api.themoviedb.org/3/search/{kind}", params=params, timeout=15).json().get("results", [])
    return res[0] if res else None

posters, report = {}, []
for jp, en, k, year in ROWS:
    kind, query, y = OVERRIDES.get(en, ("movie" if k == "film" else "tv", re.sub(r"\s*S\d.*$", "", en), int(year)))
    hit = search(kind, query, y)
    time.sleep(0.25)
    if hit and hit.get("poster_path"):
        posters[en] = hit["poster_path"]
        name = hit.get("title") or hit.get("name")
        report.append(f"OK   {jp}  ->  {name}")
    else:
        report.append(f"なし {jp}  （検索語: {query}）")

with open(os.path.join(HERE, "posters.js"), "w", encoding="utf-8") as f:
    f.write("// fetch_posters.py で自動生成\nwindow.POSTERS=" + json.dumps(posters, ensure_ascii=False, indent=1) + ";\n")

print("\n".join(report))
print(f"\nポスター取得: {len(posters)} / {len(ROWS)} 作品。posters.js を更新しました。")
