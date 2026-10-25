import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_URL = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 1. 24区ページから現職81名の正確な氏名、区、会派を取得
req = urllib.request.Request(INDEX_URL, headers=HEADERS)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8")
soup = BeautifulSoup(html, "html.parser")
ward_links = [(a.text.strip(), urllib.parse.urljoin(INDEX_URL, a["href"])) 
              for a in soup.find_all("a", href=True) 
              if a.text.strip().endswith("区") and "/shikai/page/" in a["href"]]

current_councilors = {}

for w_name, w_url in ward_links:
    try:
        req_sub = urllib.request.Request(w_url, headers=HEADERS)
        with urllib.request.urlopen(req_sub) as r:
            s_html = r.read().decode("utf-8")
    except Exception:
        continue

    s_soup = BeautifulSoup(s_html, "html.parser")
    # 各区ページの議員写真alt属性から会派と氏名を解析
    for img in s_soup.find_all("img"):
        alt = img.get("alt", "").replace(" ", "").replace(" ", "")
        if "議員の写真" in alt:
            # 例: "大阪維新の会大阪市会議員団の近藤大議員の写真"
            # 例: "公明党大阪市会議員団の山本智子議員の写真"
            import re
            m = re.match(r'^(.*?)の([^の]+?)議員の写真$', alt)
            if m:
                party = m.group(1)
                name = m.group(2)
            else:
                # 特殊ケース（会派名に含まれる「の」対策）
                # 末尾の "議員の写真" を除き、右から最初の「の」または既知の会派
                raw = alt.replace("議員の写真", "")
                parts = raw.split("議員団の")
                if len(parts) == 2:
                    party = parts[0] + "議員団"
                    name = parts[1]
                else:
                    parts = raw.split("団の")
                    if len(parts) == 2:
                        party = parts[0] + "団"
                        name = parts[1]
                    else:
                        party = "無所属"
                        name = raw

            # 「公明党大阪市会議員団中田光一郎」のようなパターンの補正
            if "中田光一郎" in name:
                name = "中田光一郎"
                party = "公明党大阪市会議員団"

            current_councilors[name] = {
                "district": w_name,
                "partyGroup": party
            }

print(f"📋 公式名簿から抽出された現職議員数: {len(current_councilors)} 名")

# 2. osakaCouncilorMaster.js を生成
master_file = PROJECT_ROOT / "frontend" / "src" / "utils" / "osakaCouncilorMaster.js"

lines = [
    "// 大阪市会 現職議員マスター（公式名簿ベース：81名）",
    "export const OSAKA_COUNCILOR_MASTER = " + json.dumps(current_councilors, ensure_ascii=False, indent=2) + ";",
    "",
    "export const OSAKA_VALID_COUNCILORS = Object.keys(OSAKA_COUNCILOR_MASTER);",
    "",
    "export function getOsakaCouncilorMasterInfo(name) {",
    "  if (!name) return { district: '大阪市会', partyGroup: '無所属' };",
    "  const clean = name.replace(/[\\s ]+/g, '');",
    "  return OSAKA_COUNCILOR_MASTER[clean] || { district: '大阪市会', partyGroup: '無所属' };",
    "}",
    ""
]

with open(master_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ {master_file} を更新しました。")
