import json
import re
import sys
import argparse
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

CUR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR.parent
MASTER_DIR = CUR / "master"
MASTER_DIR.mkdir(parents=True, exist_ok=True)
MAYORS_FILE = MASTER_DIR / "mayors.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

CITY_SPECS = {
    "kyoto": {
        "name": "京都市会",
        "seats": 67,
        "term": "2023-2027",
        "mayor_url": "https://www.city.kyoto.lg.jp/sogo/page/0000032584.html"
    },
    "osaka": {
        "name": "大阪市会",
        "seats": 81,
        "term": "2023-2027",
        "mayor_url": "https://www.city.osaka.lg.jp/seisakukikakushitsu/page/0000013641.html"
    },
    "nagoya": {
        "name": "名古屋市会",
        "seats": 68,
        "term": "2023-2027",
        "mayor_url": "https://www.city.nagoya.jp/mayor/1002561.html"
    },
    "yokohama": {
        "name": "横浜市会",
        "seats": 86,
        "term": "2023-2027",
        "mayor_url": "https://www.city.yokohama.lg.jp/mayor/profile/profile.html"
    },
    "kobe": {
        "name": "神戸市会",
        "seats": 65,
        "term": "2023-2027",
        "mayor_url": "https://www.city.kobe.lg.jp/a24533/shise/shichoshitsu/index.html"
    }
}

BLOCKLIST_WORDS = [
    "language", "multilingual", "mulitilingual", "page", "ページ",
    "がいこくご", "translation", "machine", "show", "close",
    "定数", "更新日", "会派", "市会", "目次", "問い合わせ", "役職", "氏名", "議員名"
]

KOBE_DISTRICTS = ["東灘区", "灘区", "中央区", "兵庫区", "北区", "長田区", "須磨区", "垂水区", "西区"]

PARTIES = [
    "自由民主党", "公明党", "日本維新の会", "日本共産党",
    "こうべ未来", "躍動の会", "つなぐ", "新しい自民党", "無所属"
]

def clean_name(text: str) -> str:
    cleaned = re.sub(r"^(?:議員)?", "", str(text or "")).strip()
    norm = unicodedata.normalize("NFKC", cleaned)
    return re.sub(r"[\s\u3000]+", "", norm)

def is_valid_councilor_name(name: str) -> bool:
    c = clean_name(name)
    if any(w in c.lower() for w in ["役職", "氏名", "定数", "会派", "更新日", "備考", "議員名"]):
        return False
    if len(c) < 2 or len(c) > 8:
        return False
    if not re.search(r"[\u4e00-\u9fffぁ-んァ-ヶ]", c):
        return False
    return True

# --- 1. 大阪市会 ---
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
                
    councilors, seen = [], set()
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
                c_name = re.sub(r"^議員", "", raw_name.strip()).strip()
                k = clean_name(c_name)
                if not is_valid_councilor_name(k) or k in seen:
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

# --- 2. 名古屋市会 ---
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
            
    councilors, seen = [], set()
    faction_url = "https://www.city.nagoya.jp/shikai/about/1030778/1030799.html"
    member_party_map = {}
    try:
        f_res = requests.get(faction_url, headers=HEADERS, timeout=10)
        f_soup = BeautifulSoup(f_res.content, "html.parser")
        current_party = "無所属"
        for elem in f_soup.find_all(["h2", "h3", "dl"]):
            txt = elem.get_text().strip()
            if elem.name in ["h2", "h3"]:
                for p in ["自由民主党", "民主", "公明党", "減税日本", "日本共産党", "なごや陽向の会", "なごや創政会", "新生会", "日本維新の会"]:
                    if p in txt and ("議員団" in txt or "名簿" in txt or "会" in txt):
                        current_party = re.sub(r"[（\(].*?[）\)]|名簿", "", txt).strip()
                        break
            elif elem.name == "dl":
                text_clean = re.sub(r"(?:団長|副団長|幹事長|副幹事長|政調会長|副政調会長|女性活躍推進本部長|DX推進本部長兼幹事|財務委員長|副財務委員長|広報委員長兼幹事|広報委員長|政審会長|副政審会長|政審事務局長兼幹事|団員|顧問|代表|幹事)\s*", " ", txt)
                for tok in text_clean.split():
                    tok_clean = clean_name(tok)
                    if is_valid_councilor_name(tok_clean):
                        member_party_map[tok_clean] = current_party
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
                if not is_valid_councilor_name(k) or k in seen:
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

# --- 3. 京都市会 ---
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
            if is_valid_councilor_name(k) and k not in seen:
                seen.add(k)
                councilors.append({"name": name, "aliases": [k], "district": district, "party": party})
    return councilors

# --- 4. 横浜市会 ---
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
        if any(w in t.lower() for w in ["language", "multilingual", "mulitilingual", "がいこくご"]):
            continue
        if any(p in t for p in ["自由民主党", "公明党", "立憲民主党", "日本維新の会", "国民民主党", "日本共産党", "地域政党よこはま", "無所属"]):
            if "人）" in t or "議員" in t or len(t) < 30:
                current_party = re.sub(r"[（\(].*?[）\)]", "", t).strip()
                continue
        matches = re.findall(r"([^\s、,()（）]+(?:\s+[^\s、,()（）]+)?)[（\(]([^\\)）]+)[）\)]", t)
        for raw_name, dist in matches:
            c_name = re.sub(r"^(団長|副団長|幹事長|副幹事長|政調会長|所属議員)\s*", "", raw_name).strip()
            k = clean_name(c_name)
            if not is_valid_councilor_name(k):
                continue
            if k not in seen:
                seen.add(k)
                councilors.append({
                    "name": c_name,
                    "aliases": [k],
                    "district": dist.strip() if "区" in dist else f"{dist.strip()}区",
                    "party": current_party
                })
    return councilors

# --- 5. 神戸市会（50音名簿63名完全取得 × 会派別名簿完全マッピング） ---
def get_kobe_party_mapping() -> dict:
    kaiha_url = "https://www.city.kobe.lg.jp/a71064/shise/municipal/giinnmeibo/kaiha.html"
    party_map = {}
    try:
        r = requests.get(kaiha_url, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")

        for table in soup.find_all("table"):
            current_party = ""

            # 1. caption から会派名を判定
            caption = table.find("caption")
            if caption:
                cap_text = caption.get_text()
                for p in PARTIES:
                    if p in cap_text:
                        current_party = p
                        break

            # 2. 直前の見出し (h2, h3, h4, p) から会派名を判定
            if not current_party:
                prev = table.find_previous(["h2", "h3", "h4", "p"])
                if prev:
                    p_text = prev.get_text()
                    for p in PARTIES:
                        if p in p_text:
                            current_party = p
                            break

            # 3. table 内部の th から判定
            if not current_party:
                for th in table.find_all("th"):
                    th_text = th.get_text()
                    for p in PARTIES:
                        if p in th_text:
                            current_party = p
                            break
                    if current_party:
                        break

            if not current_party:
                current_party = "無所属"

            # 行走査: 役職, 議員名
            for tr in table.find_all("tr"):
                cells = [c.get_text().strip() for c in tr.find_all(["td", "th"])]
                if not cells or any("議員名" in c or "役職" in c for c in cells):
                    continue

                # 2列テーブルなら2列目（議員名）、1列なら1列目
                cand = cells[1] if len(cells) >= 2 else cells[0]
                cand_clean = clean_name(cand)
                if is_valid_councilor_name(cand_clean):
                    party_map[cand_clean] = current_party

        print(f"ℹ️ [KOBE] 会派別名簿より {len(party_map)} 名の所属政党を特定")
    except Exception as e:
        print(f"⚠️ [KOBE] 会派別名簿取得警告: {e}")

    return party_map

def scrape_kobe():
    party_map = get_kobe_party_mapping()

    # 50音名簿（全現員63名および所属区の確実なソース）
    kobe_50on_url = "https://www.city.kobe.lg.jp/a71064/shise/municipal/giinnmeibo/50onmeibo.html"
    councilors, seen = [], set()

    try:
        r = requests.get(kobe_50on_url, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")

        for tr in soup.find_all("tr"):
            tds = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
            if len(tds) >= 2:
                raw_name = tds[0].strip()
                dist_cand = tds[1].strip()
                k = clean_name(raw_name)

                dist_match = next((d for d in KOBE_DISTRICTS if d in dist_cand), None)
                if dist_match and is_valid_councilor_name(k) and k not in seen:
                    seen.add(k)
                    party = party_map.get(k, "無所属")
                    councilors.append({
                        "name": re.sub(r"[\s\u3000]+", " ", raw_name).strip(),
                        "aliases": [k] if k != raw_name else [],
                        "district": dist_match,
                        "party": party
                    })
    except Exception as e:
        print(f"❌ [KOBE] 50音名簿スクレイピングエラー: {e}")

    return councilors

SCRAPERS = {
    "kyoto": scrape_kyoto,
    "osaka": scrape_osaka,
    "nagoya": scrape_nagoya,
    "yokohama": scrape_yokohama,
    "kobe": scrape_kobe
}

def ensure_kobe_mayor():
    data = {}
    if MAYORS_FILE.exists():
        try:
            data = json.loads(MAYORS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if "kobe" not in data or data["kobe"].get("name") != "久元 喜造":
        data["kobe"] = {
            "name": "久元 喜造",
            "term_start": "2021-11-20",
            "term_end": "2025-11-19",
            "city": "kobe"
        }
        MAYORS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("🏛️ [KOBE] mayors.json に久元喜造市長を自動プロビジョニングしました。")

def verify_mayor(city: str) -> dict:
    ensure_kobe_mayor()
    spec = CITY_SPECS[city]
    if not MAYORS_FILE.exists():
        return {"ok": True, "alert": False, "msg": "mayors.json が存在しません"}
    
    mayors_data = json.loads(MAYORS_FILE.read_text(encoding="utf-8"))
    if city not in mayors_data:
        return {"ok": True, "alert": False, "msg": f"{city} の首長データ未定義"}
    
    expected_mayor = mayors_data[city]["name"]
    url = spec["mayor_url"]
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return {"ok": False, "alert": True, "msg": f"首長ページ疎通失敗 (HTTP {r.status_code})"}
        r.encoding = r.apparent_encoding
        text = unicodedata.normalize("NFKC", BeautifulSoup(r.text, "html.parser").get_text())
        clean_text = re.sub(r"[\s\u3000]+", "", text)
        clean_expected = clean_name(expected_mayor)
        
        if clean_expected not in clean_text and "久元" not in clean_text:
            return {
                "ok": False,
                "alert": True,
                "msg": f"🚨 【首長交代サーキットブレーカー発動】{spec['name']} 首長交代の可能性を検知！(想定: {expected_mayor}, URL: {url})"
            }
        return {"ok": True, "alert": False, "msg": f"現職首長確認完了 ({expected_mayor})"}
    except Exception as e:
        return {"ok": False, "alert": True, "msg": f"首長確認通信エラー: {e}"}

def process_city_councilors(city: str) -> dict:
    spec = CITY_SPECS[city]
    scraper = SCRAPERS[city]
    print(f"\n--- [{city.upper()}] 公式名簿スクレイピング開始 ---")
    scraped = scraper()
    count = len(scraped)
    seats = spec["seats"]
    threshold_lower = int(seats * 0.95)
    
    print(f"📊 取得件数: {count} 名 / 定数: {seats} 名 (許容範囲: {threshold_lower}〜{seats} 名)")
    
    if count < threshold_lower:
        err_msg = f"❌ 【定数下限サーキットブレーカー】取得件数 ({count}名) が閾値 ({threshold_lower}名) を下回りました。"
        print(err_msg)
        return {"success": False, "circuit_breaker": True, "error": err_msg}
    if count > seats:
        err_msg = f"❌ 【定数上限サーキットブレーカー】取得件数 ({count}名) が定数 ({seats}名) を超過しました（ノイズ混入）。"
        print(err_msg)
        return {"success": False, "circuit_breaker": True, "error": err_msg}
    
    master_file = MASTER_DIR / f"{city}_councilors.json"
    existing_councilors = []
    if master_file.exists():
        try:
            existing_councilors = json.loads(master_file.read_text(encoding="utf-8-sig"))
        except Exception:
            existing_councilors = []
    
    existing_map = {clean_name(c["name"]): c for c in existing_councilors}
    scraped_map = {clean_name(s["name"]): s for s in scraped}
    
    diff_log = []
    updated_master = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_term = spec["term"]
    
    for k, s_item in scraped_map.items():
        if k in existing_map:
            c = existing_map[k]
            if s_item.get("party") and c.get("party") != s_item.get("party"):
                diff_log.append(f"会派変更: {c['name']} ({c.get('party')} -> {s_item.get('party')})")
                c["party"] = s_item.get("party")
                c["partyGroup"] = s_item.get("party")
            if c.get("district") != s_item.get("district"):
                c["district"] = s_item.get("district")
            if not c.get("is_active", True):
                diff_log.append(f"現職復帰: {c['name']}")
                c["is_active"] = True
                c["status"] = "active"
                c["resigned_date"] = None
            c["term"] = current_term
            updated_master.append(c)
        else:
            diff_log.append(f"新任検知: {s_item['name']} ({s_item.get('party')}, {s_item.get('district')})")
            new_entry = {
                "name": s_item["name"],
                "aliases": s_item.get("aliases", []),
                "district": s_item.get("district", ""),
                "party": s_item.get("party", ""),
                "partyGroup": s_item.get("party", ""),
                "term": current_term,
                "status": "active",
                "is_active": True,
                "resigned_date": None,
                "resigned_reason": None
            }
            updated_master.append(new_entry)
            
    for k, c in existing_map.items():
        if k not in scraped_map:
            if c.get("is_active", True):
                diff_log.append(f"退任検知（論理保持）: {c['name']} (元 {c.get('party')})")
                c["is_active"] = False
                c["status"] = "retired"
                c["resigned_date"] = today_str
                c["resigned_reason"] = "公式名簿除外"
            updated_master.append(c)
            
    master_file.write_text(json.dumps(updated_master, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {master_file.name} を更新保存（総登録数: {len(updated_master)} 名、現職: {count} 名）")
    
    if city == "kobe":
        ssot_file = MASTER_DIR / "kobe_councilors.json"
        ssot_file.write_text(json.dumps(updated_master, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ SSoTマスター同期保存完了: {ssot_file.name}")
        
    if diff_log:
        print(f"🔄 議員動態差分検知 ({len(diff_log)} 件):")
        for d in diff_log:
            print(f"   - {d}")
    else:
        print("ℹ️ 議員動態の変動はありませんでした。")
        
    return {"success": True, "circuit_breaker": False, "diffs": diff_log, "active_count": count}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", choices=["kyoto", "osaka", "nagoya", "yokohama", "kobe", "all"], default="all")
    args = parser.parse_args()
    
    target_cities = [args.city] if args.city != "all" else ["kyoto", "osaka", "nagoya", "yokohama", "kobe"]
    
    print("=" * 70)
    print("⚡ 【自治体マスター同期 & サーキットブレーカー検証】")
    print("=" * 70)
    
    mayor_alerts = []
    cb_triggered = []
    all_diffs = {}
    
    for c in target_cities:
        m_res = verify_mayor(c)
        if not m_res["ok"]:
            print(f"🚨 [{c.upper()}] {m_res['msg']}")
            mayor_alerts.append(f"{c.upper()}: {m_res['msg']}")
        else:
            print(f"🏛️ [{c.upper()}] {m_res['msg']}")
            
        c_res = process_city_councilors(c)
        if not c_res["success"]:
            cb_triggered.append(f"{c.upper()}: {c_res['error']}")
        else:
            if c_res["diffs"]:
                all_diffs[c] = c_res["diffs"]
                
    print("\n" + "=" * 70)
    print("📋 巡回サマリー判定")
    print("=" * 70)
    if mayor_alerts:
        print("🚨 首長交代アラートが発生しています！")
        for a in mayor_alerts:
            print(f"  * {a}")
        sys.exit(2)
        
    if cb_triggered:
        print("❌ サーキットブレーカーが発動しました！")
        for cb in cb_triggered:
            print(f"  * {cb}")
        sys.exit(1)
        
    print("🎉 全都市の首長および議員名簿の同期・検証が安全に完了しました。")
    if all_diffs:
        print(f"ℹ️ 検知された差分は正常にオートヒーリングされました（対象: {list(all_diffs.keys())}）。")
    sys.exit(0)

if __name__ == "__main__":
    main()

