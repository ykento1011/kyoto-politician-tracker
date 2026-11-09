import json
import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "frontend" / "dist"
PUBLIC_DIR = ROOT_DIR / "frontend" / "public"
DATA_DIR = PUBLIC_DIR / "data"

CITY_CONFIGS = {
    "kyoto": {
        "council_name": "京都市会",
        "official_url": "https://www.city.kyoto.lg.jp/shikai/",
        "election_commission": "京都市選挙管理委員会",
        "ogp": "https://gikai-mikata.jp/ogp-kyoto.png"
    },
    "osaka": {
        "council_name": "大阪市会",
        "official_url": "https://www.city.osaka.lg.jp/shikai/",
        "election_commission": "大阪市選挙管理委員会",
        "ogp": "https://gikai-mikata.jp/ogp-osaka.png"
    },
    "nagoya": {
        "council_name": "名古屋市会",
        "official_url": "https://www.city.nagoya.jp/shikai/",
        "election_commission": "名古屋市選挙管理委員会",
        "ogp": "https://gikai-mikata.jp/ogp-nagoya.png"
    },
    "yokohama": {
        "council_name": "横浜市会",
        "official_url": "https://www.city.yokohama.lg.jp/shikai/",
        "election_commission": "横浜市選挙管理委員会",
        "ogp": "https://gikai-mikata.jp/ogp-yokohama.png"
    },
    "kobe": {
        "council_name": "神戸市会",
        "official_url": "https://www.city.kobe.lg.jp/shikai/",
        "election_commission": "神戸市選挙管理委員会",
        "ogp": "https://gikai-mikata.jp/ogp-kobe.png"
    }
}

def clean_speaker_name(name: str) -> str:
    return name.replace(" ", "").replace(" ", "").strip()

def run_ssg():
    print("=================================================================")
    print("全365議員 構造化データ（JSON-LD）静的生成 & sitemap.xml 構築")
    print("=================================================================")

    # 1. 既存写真ファイルのインデックス
    photo_dir = PUBLIC_DIR / "councilors"
    existing_photos = {}
    if photo_dir.exists():
        for p in photo_dir.glob("*.*"):
            clean_stem = clean_speaker_name(p.stem)
            existing_photos[clean_stem] = p.name

    # 2. 全365議員の収集
    councilors_by_city = {}
    total_active = 0

    for city, cfg in CITY_CONFIGS.items():
        c_file = DATA_DIR / f"{city}_councilors.json"
        p_file = DATA_DIR / f"{city}_pledge_tracker.json"
        
        pledge_data = {}
        if p_file.exists():
            try:
                pledge_data = json.loads(p_file.read_text(encoding="utf-8"))
            except Exception:
                pledge_data = {}

        if not c_file.exists():
            print(f"⚠️ {c_file} が見つかりません。")
            continue

        raw_list = json.loads(c_file.read_text(encoding="utf-8"))
        # 現職（is_active True かつ resigned_date なし）
        active = [c for c in raw_list if c.get("is_active", True) and not c.get("resigned_date")]
        councilors_by_city[city] = []

        for c in active:
            name = c.get("name", "").strip()
            clean_name = clean_speaker_name(name)
            party = c.get("partyGroup") or c.get("party", "無所属")
            district = c.get("district", "")
            
            # 写真判定（存在しない場合は共通OGPにフェイルセーフフォールバック）
            if clean_name in existing_photos:
                image_url = f"https://gikai-mikata.jp/councilors/{existing_photos[clean_name]}"
            else:
                image_url = cfg["ogp"]

            # sameAs（公約原本・選挙公報URLなど）
            same_as = []
            if name in pledge_data and pledge_data[name].get("bulletin_url"):
                b_url = pledge_data[name]["bulletin_url"]
                if b_url.startswith("http"):
                    same_as.append(b_url)
            elif clean_name in pledge_data and pledge_data[clean_name].get("bulletin_url"):
                b_url = pledge_data[clean_name]["bulletin_url"]
                if b_url.startswith("http"):
                    same_as.append(b_url)

            councilors_by_city[city].append({
                "name": name,
                "clean_name": clean_name,
                "party": party,
                "district": district,
                "image_url": image_url,
                "same_as": same_as
            })

        print(f"  [{city.upper()}] 現職議員: {len(councilors_by_city[city])} 名")
        total_active += len(councilors_by_city[city])

    print(f"\n👉 合計現職議員: {total_active} 名 (365名一致判定: {'✅ OK' if total_active == 365 else '⚠️ NG'})")

    # 3. dist が存在する場合は静的 HTML の事前生成
    if DIST_DIR.exists():
        template_path = DIST_DIR / "index.html"
        if template_path.exists():
            base_html = template_path.read_text(encoding="utf-8")
            generated_pages = 0

            for city, councilor_list in councilors_by_city.items():
                cfg = CITY_CONFIGS[city]
                city_dir = DIST_DIR / city / "politicians"
                city_dir.mkdir(parents=True, exist_ok=True)

                for c in councilor_list:
                    speaker_id = c["clean_name"]
                    target_url = f"https://gikai-mikata.jp/{city}/?speaker={urllib.parse.quote(c['name'])}"
                    page_title = f"{c['name']}（{cfg['council_name']}・{c['district']}）の政策・公約・採決態度 ｜ 議会のミカタ"
                    page_desc = f"{cfg['council_name']}（{c['district']}・{c['party']}）{c['name']}議員。重点公約、議案採決態度、および質疑実績ログの可視化データ。"

                    # Schema.org/Person JSON-LD
                    person_entity = {
                        "@type": "Person",
                        "@id": f"{target_url}#person",
                        "name": c["name"],
                        "jobTitle": f"{cfg['council_name']}議員",
                        "worksFor": {
                            "@type": "GovernmentOrganization",
                            "name": cfg["council_name"],
                            "url": cfg["official_url"]
                        },
                        "memberOf": {
                            "@type": "Organization",
                            "name": c["party"]
                        },
                        "description": page_desc,
                        "image": c["image_url"],
                        "url": target_url,
                        "hasCredential": {
                            "@type": "EducationalOccupationalCredential",
                            "credentialCategory": "ElectedOfficial",
                            "recognizedBy": {
                                "@type": "GovernmentOrganization",
                                "name": cfg["election_commission"]
                            }
                        }
                    }
                    if c["same_as"]:
                        person_entity["sameAs"] = c["same_as"]

                    json_ld = {
                        "@context": "https://schema.org",
                        "@type": "ProfilePage",
                        "mainEntity": person_entity
                    }
                    

                    json_ld_str = json.dumps(json_ld, ensure_ascii=False, indent=2)

                    # HTML 注入
                    page_html = base_html
                    page_html = re.sub(r"<title>.*?</title>", f"<title>{page_title}</title>", page_html)
                    page_html = re.sub(r'<meta\s+name="description"\s+content=".*?"\s*/?>', f'<meta name="description" content="{page_desc}" />', page_html)
                    page_html = re.sub(r'<link\s+rel="canonical"\s+href=".*?"\s*/?>', f'<link rel="canonical" href="{target_url}" />', page_html)
                    page_html = re.sub(r'<meta\s+property="og:url"\s+content=".*?"\s*/?>', f'<meta property="og:url" content="{target_url}" />', page_html)
                    page_html = re.sub(r'<meta\s+property="og:title"\s+content=".*?"\s*/?>', f'<meta property="og:title" content="{page_title}" />', page_html)
                    page_html = re.sub(r'<meta\s+property="og:description"\s+content=".*?"\s*/?>', f'<meta property="og:description" content="{page_desc}" />', page_html)
                    page_html = re.sub(r'<meta\s+property="og:image"\s+content=".*?"\s*/?>', f'<meta property="og:image" content="{c["image_url"]}" />', page_html)

                    # JSON-LD 注入
                    json_ld_tag = f'\n  <script type="application/ld+json">\n{json_ld_str}\n  </script>\n</head>'
                    page_html = page_html.replace("</head>", json_ld_tag)

                    # /{city}/politicians/{speaker_id}/index.html として配置
                    pol_file_dir = city_dir / speaker_id
                    pol_file_dir.mkdir(parents=True, exist_ok=True)
                    (pol_file_dir / "index.html").write_text(page_html, encoding="utf-8")
                    generated_pages += 1

            print(f"✨ [SSG] 全 {generated_pages} 議員の静的 HTML (JSON-LD 注入済) を生成しました。")

    # 4. sitemap.xml の生成（計 371 URL）
    today = datetime.now().strftime("%Y-%m-%d")
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # トップポータル (1URL)
    sitemap_lines.append(f"""  <url>
    <loc>https://gikai-mikata.jp/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

    # 5都市ダッシュボード (5URL)
    for city in CITY_CONFIGS.keys():
        sitemap_lines.append(f"""  <url>
    <loc>https://gikai-mikata.jp/{city}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")

    # 全365議員 (365URL)
    councilor_url_count = 0
    for city, councilor_list in councilors_by_city.items():
        for c in councilor_list:
            councilor_url_count += 1
            speaker_param = urllib.parse.quote(c["clean_name"])
            url = f"https://gikai-mikata.jp/{city}/?speaker={urllib.parse.quote(c['name'])}"
            sitemap_lines.append(f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

    sitemap_lines.append('</urlset>')
    sitemap_content = "\n".join(sitemap_lines)

    # public および dist の両方に書き出し
    (PUBLIC_DIR / "sitemap.xml").write_text(sitemap_content, encoding="utf-8")
    if DIST_DIR.exists():
        (DIST_DIR / "sitemap.xml").write_text(sitemap_content, encoding="utf-8")

    total_urls = 1 + len(CITY_CONFIGS) + councilor_url_count
    print(f"\n🗺️ [Sitemap] sitemap.xml を生成完了: 総URL数 = {total_urls} (要求仕様: 371 URL)")
    if total_urls == 371:
        print("  ✅ 371 URL（ポータル1 + 5都市5 + 365議員）完全一致確認！")
    else:
        print(f"  ⚠️ URL数不一致: {total_urls} != 371")

if __name__ == "__main__":
    run_ssg()
