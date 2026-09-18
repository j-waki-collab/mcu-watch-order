"""相関図の顔写真を Wikipedia / Wikimedia Commons から取ってきて people.js を作る。

TMDBのトークンは不要。写真は自由に使えるライセンスのものだけを採用し、
撮影者とライセンス名も一緒に保存する（表示ページでクレジットに使う）。
"""
import json, os, re, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
html_text = open(os.path.join(HERE, "chart.html"), encoding="utf-8").read()
ACTORS = []
for m in re.finditer(r'^\s*\w+:\["[^"]+","([^"]+)","[^"]+"\]', html_text, re.M):
    if m.group(1) not in ACTORS:
        ACTORS.append(m.group(1))

S = requests.Session()
S.headers["User-Agent"] = "mcu-watch-order/1.0 (personal, non-commercial)"
API = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"

# 使えるライセンスだけ通す（パブリックドメインとクリエイティブ・コモンズ）
OK_LICENSE = re.compile(r"(cc[- ]by|public domain|cc0|pd-)", re.I)

def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]

thumbs, files = {}, {}
for group in chunks(ACTORS, 10):
    for attempt in range(6):
        r = S.get(API, params={"action": "query", "format": "json", "redirects": 1,
                               "prop": "pageimages", "piprop": "thumbnail|name",
                               "pithumbsize": 400, "titles": "|".join(group)}, timeout=25)
        if r.status_code != 429:
            break
        time.sleep(20 * (attempt + 1))
    r.raise_for_status()
    q = r.json()["query"]
    alias = {n["to"]: n["from"] for n in q.get("normalized", [])}
    alias.update({n["to"]: n["from"] for n in q.get("redirects", [])})
    for p in q["pages"].values():
        name = p.get("title", "")
        name = alias.get(name, name)
        if p.get("thumbnail") and p.get("pageimage"):
            thumbs[name] = p["thumbnail"]["source"].split("?")[0]
            files[name] = "File:" + p["pageimage"]
    time.sleep(1.5)

# 記事にページ画像がない人は Wikidata の画像プロパティ(P18)から探す
missing = [a for a in ACTORS if a not in thumbs]
for group in chunks(missing, 10):
    r = S.get(API, params={"action": "query", "format": "json", "redirects": 1,
                           "prop": "pageprops", "ppprop": "wikibase_item",
                           "titles": "|".join(group)}, timeout=25)
    if r.status_code != 200:
        continue
    q = r.json().get("query", {})
    alias = {n["to"]: n["from"] for n in q.get("normalized", [])}
    alias.update({n["to"]: n["from"] for n in q.get("redirects", [])})
    qids = {}
    for pg in q.get("pages", {}).values():
        name = alias.get(pg.get("title", ""), pg.get("title", ""))
        qid = (pg.get("pageprops") or {}).get("wikibase_item")
        if qid:
            qids[name] = qid
    for name, qid in qids.items():
        rr = S.get("https://www.wikidata.org/w/api.php",
                   params={"action": "wbgetclaims", "format": "json", "entity": qid, "property": "P18"}, timeout=25)
        time.sleep(1.0)
        if rr.status_code != 200:
            continue
        claims = rr.json().get("claims", {}).get("P18", [])
        if not claims:
            continue
        fname = claims[0]["mainsnak"]["datavalue"]["value"]
        thumbs[name] = "https://commons.wikimedia.org/wiki/Special:FilePath/" + requests.utils.quote(fname) + "?width=400"
        files[name] = "File:" + fname
    time.sleep(1.5)

people, report = {}, []
for group in chunks([a for a in ACTORS if a in files], 10):
    for attempt in range(5):
        r = S.get(COMMONS, params={"action": "query", "format": "json",
                               "prop": "imageinfo", "iiprop": "extmetadata",
                               "titles": "|".join(files[a] for a in group)}, timeout=25)
        if r.status_code != 429:
            break
        time.sleep(20 * (attempt + 1))
    r.raise_for_status()
    meta = {}
    for p in r.json()["query"]["pages"].values():
        info = (p.get("imageinfo") or [{}])[0].get("extmetadata", {})
        meta[(p.get("title") or "").replace("_", " ")] = info
    for a in group:
        info = meta.get(files[a].replace("_", " "), {})
        lic = (info.get("LicenseShortName", {}) or {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", (info.get("Artist", {}) or {}).get("value", "")).strip()
        if lic and OK_LICENSE.search(lic):
            people[a] = {"u": thumbs[a], "by": artist[:60], "lic": lic}
            report.append(f"OK   {a}  ({lic})")
        else:
            report.append(f"除外 {a}  （ライセンス: {lic or '不明'}）")
    time.sleep(0.3)

for a in ACTORS:
    if a not in people and not any(r.startswith("除外 " + a) for r in report):
        report.append(f"なし {a}")

with open(os.path.join(HERE, "people.js"), "w", encoding="utf-8") as f:
    f.write("// fetch_people_wiki.py で自動生成（Wikipedia / Wikimedia Commons）\nwindow.PEOPLE=" +
            json.dumps(people, ensure_ascii=False, indent=1) + ";\n")

print("\n".join(report))
print(f"\n顔写真: {len(people)} / {len(ACTORS)} 人。people.js を更新しました。")
