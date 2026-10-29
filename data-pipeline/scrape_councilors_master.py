import json
import re
import argparse
from pathlib import Path
import requests
from bs4 import BeautifulSoup

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
MASTER_DIR = CUR / "master"
FRONTEND_DATA = PROJECT_ROOT / "frontend" / "public" / "data"
IMG_BASE = PROJECT_ROOT / "frontend" / "public" / "councilors"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_name(text: str) -> str:
    # 先頭の「議員」、空白、全角スペースを完全除去
    cleaned = re.sub(r"^(?:議員)?", "", str(text or "")).strip()
    return re.sub(r"[\s\u3000]+", "", cleaned)

# 1. 大阪市会
def scrape_osaka():
    top_url = "https://www.city.osaka.lg.jp/shikai/page/0000310422.html"
    res = requests.get(top_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.content, "html.parser")
    
    district_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/shikai/page/0000310" in href and href != top_url:
            if not href.startswith("http"):
                href = f"https://www.city.osaka.lg.jp{href}"
            txt = a.get_text().strip()
            if not any(k in txt for k in ["本文", "トップ", "管理", "正字"]):
                district_links.append((txt, href))
                
    councilors = []
    seen = set()
    
    for label, d_url in district_links:
        try:
            r = requests.get(d_url, headers=HEADERS, timeout=10)
            d_soup = BeautifulSoup(r.content, "html.parser")
            
            title = d_soup.find("h1") or d_soup.find("title")
            d_match = re.search(r"選挙区別名簿[（\(](.*?)[）\)]", title.get_text() if title else label)
            district = d_match.group(1).strip() if d_match else label
            if district and not district.endswith("区"):
                district = f"{district}区"
                
            text = d_soup.get_text()
            entries = re.findall(r"([^\s\n ]+(?:\s+[^\s\n ]+)?)[（\(]([ぁ-ん\s]+)[）\)].*?所属会派[：:]\s*([^\n\r/／期\s]+)", text, re.DOTALL)
            for raw_name, furigana, party_line in entries:
                # 取得した生名から「議員」を除去
                c_name = re.sub(r"^議員", "", raw_name.strip()).strip()
                k = clean_name(c_name)
                if k in seen or "氏名" in k or len(k) < 2:
                    continue
                seen.add(k)
                
                furi = clean_name(furigana)
                aliases = [furi] if furi and furi != k else []
                party = party_line.strip()
                
                councilors.append({
                    "name": c_name,
                    "aliases": aliases,
                    "district": district,
                    "party": party
                })
        except Exception:
            pass
            
    return councilors

# 2. 名古屋市会
def scrape_nagoya():
    top_url = "https://www.city.nagoya.jp/shikai/about/1030778/1030779/index.html"
    res = requests.get(top_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.content, "html.parser")
    
    district_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = a.get_text().strip()
        if "区" in txt and ("10307" in href or "shikai" in href):
            if not href.startswith("http"):
                href = f"https://www.city.nagoya.jp{href}" if href.startswith("/") else f"https://www.city.nagoya.jp/shikai/about/1030778/1030779/{href}"
            district_links.append((txt, href))
            
    councilors = []
    seen = set()
    
    faction_url = "https://www.city.nagoya.jp/shikai/about/1030778/1030799.html"
    member_party_map = {}
    try:
        f_res = requests.get(faction_url, headers=HEADERS, timeout=10)
        f_soup = BeautifulSoup(f_res.content, "html.parser")
        current_party = "無所属"
        for elem in (f_soup.find("div", id="main") or f_soup).find_all(["h2", "h3", "p", "td", "li"]):
            t = elem.get_text().strip()
            if any(p in t for p in ["自由民主党", "民主", "公明党", "減税日本", "日本共産党"]):
                if "議員団" in t or "名簿" in t:
                    current_party = t.replace("名簿", "").strip()
            for w in re.findall(r"[\u4e00-\u9fffぁ-んァ-ヶ]{2,5}", t):
                if len(w) >= 2 and w not in ["団長", "副団長", "幹事長", "議員", "顧問", "委員長"]:
                    member_party_map[clean_name(w)] = current_party
    except Exception:
        pass

    for dist_label, d_url in district_links:
        try:
            r = requests.get(d_url, headers=HEADERS, timeout=10)
            d_soup = BeautifulSoup(r.content, "html.parser")
            text = d_soup.get_text()
            d_clean = re.sub(r"[（\(].*?[）\)]", "", dist_label).strip()
            if not d_clean.endswith("区"):
                d_match = re.search(r"(\w+区)", text)
                d_clean = d_match.group(1) if d_match else dist_label

            matches = re.findall(r"([^\s\n（\()]+)[（\(]([ぁ-ん\s]+)[）\)]", text)
            for name, furi in matches:
                k = clean_name(name)
                if k in seen or len(k) < 2 or "議員名簿" in k:
                    continue
                seen.add(k)
                party = member_party_map.get(k, "無所属")
                councilors.append({
                    "name": name.strip(),
                    "aliases": [clean_name(furi)] if clean_name(furi) != k else [],
                    "district": d_clean,
                    "party": party
                })
        except Exception:
            pass
    return councilors

# 3. 京都市会
def scrape_kyoto():
    url = "https://www2.city.kyoto.lg.jp/shikai/meibo/gojuon.html"
    res = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.content, "html.parser")
    councilors, seen = [], set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 3:
            name, party, district = tds[0].get_text().strip(), tds[1].get_text().strip(), tds[2].get_text().strip()
            k = clean_name(name)
            if k and "名前" not in k and "議員" not in k and k not in seen:
                seen.add(k)
                councilors.append({"name": name, "aliases": [k], "district": district, "party": party})
    return councilors

# 4. 横浜市会
def scrape_yokohama():
    url = "https://www.city.yokohama.lg.jp/shikai/giin/kaihabetsu.html"
    res = requests.get(url, headers=HEADERS, timeout=15)
    for enc in ["utf-8", "cp932", res.apparent_encoding]:
        try:
            text = res.content.decode(enc)
            if "議員" in text:
                break
        except Exception:
            continue
    else:
        text = res.text

    soup = BeautifulSoup(text, "html.parser")
    councilors, seen = [], set()
    current_party = "無所属"
    content = soup.find("div", class_="contents") or soup
    
    for elem in content.find_all(["h2", "h3", "p", "li", "td"]):
        t = elem.get_text().strip()
        # メニュー文字列や政党名そのものを弾く
        if t in ["Language", "MulitilingualPage", "LanguageMulitilingualPage"] or len(t) < 2:
            continue
        
        if any(p in t for p in ["自由民主党", "公明党", "立憲民主党", "日本維新の会", "国民民主党", "日本共産党", "地域政党よこはま", "無所属"]):
            if "人）" in t or "議員" in t or len(t) < 30:
                current_party = re.sub(r"[（\(].*?[）\)]", "", t).strip()
                continue # 政党名そのものを議員として登録しない
                
        matches = re.findall(r"([^\s、,()（）]+(?:\s+[^\s、,()（）]+)?)[（\(]([^\)）]+)[）\)]", t)
        for raw_name, dist in matches:
            c_name = re.sub(r"^(団長|副団長|幹事長|副幹事長|政調会長|所属議員)\s*", "", raw_name).strip()
            k = clean_name(c_name)
            if len(k) >= 2 and k not in seen and not any(w in k for w in ["定数", "更新日", "会派", "市会", "党", "所属"]):
                seen.add(k)
                councilors.append({"name": c_name, "aliases": [k], "district": dist.strip() if "区" in dist else f"{dist.strip()}区", "party": current_party})
    return councilors

# ----------------------------------------------------
# 実行 & 画像照合
# ----------------------------------------------------
def main():
    print("=" * 70)
    print("⚡ 【最終確定】4都市公式名簿スクレイピング＆画像照合")
    print("=" * 70)
    
    for city, func in [("kyoto", scrape_kyoto), ("yokohama", scrape_yokohama), ("osaka", scrape_osaka), ("nagoya", scrape_nagoya)]:
        res = func()
        if len(res) >= 50:
            m_file = MASTER_DIR / f"councilors_{city}.json"
            m_file.write_bytes(json.dumps(res, ensure_ascii=False, indent=2).encode("utf-8"))
            
            stats_dict = {}
            for c in res:
                name = c["name"]
                c_name = clean_name(name)
                entry = {"name": name, "party": c.get("party", ""), "district": c.get("district", ""), "aliases": c.get("aliases", [])}
                stats_dict[name] = entry
                if c_name != name:
                    stats_dict[c_name] = entry
                for al in c.get("aliases", []):
                    stats_dict[clean_name(al)] = entry
                    
            (FRONTEND_DATA / f"{city}_speaker_stats.json").write_bytes(json.dumps(stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
            if city == "kyoto":
                (FRONTEND_DATA / "speaker_stats.json").write_bytes(json.dumps(stats_dict, ensure_ascii=False, indent=2).encode("utf-8"))
            
            # 画像照合
            img_dir = IMG_BASE / city
            existing_files = list(img_dir.glob("*")) if img_dir.exists() else []
            file_map = {clean_name(f.stem): f.name for f in existing_files if f.is_file()}
            
            missing = []
            for c in res:
                name = c["name"]
                k = clean_name(name)
                found = False
                if k in file_map:
                    found = True
                else:
                    for al in c.get("aliases", []):
                        if clean_name(al) in file_map:
                            found = True
                            break
                if not found:
                    missing.append(name)
            
            print(f"✅ [{city.upper()}] 現職: {len(res)} 名 | 📸 画像一致: {len(res) - len(missing)} 名 / 未格納: {len(missing)} 名")
            if missing:
                print(f"   🚨 画像欠損: {missing}")
        else:
            print(f"⚠️ [{city.upper()}] 取得失敗 ({len(res)} 件)")

if __name__ == "__main__":
    main()
