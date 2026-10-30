from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
INDEX_HTML = FRONTEND / "index.html"
PUBLIC = FRONTEND / "public"

CITIES = {
    "kyoto": {
        "name": "京都市会",
        "title": "京都市会 議会のミカタ ｜ AIは入口。判断するのは市民です。",
        "desc": "京都市会公式会議録と議決データを客観的に構造化。松井市長の政策・予算進捗、議員質疑の4軸分析、賛否が分かれた議案ログを一次情報原本で確認できるオープンデータ基盤。",
        "image": "https://gikai-mikata.jp/ogp-kyoto.png",
        "url": "https://gikai-mikata.jp/kyoto/"
    },
    "osaka": {
        "name": "大阪市会",
        "title": "大阪市会 議会のミカタ ｜ AIは入口。判断するのは市民です。",
        "desc": "大阪市会公式会議録と議決データを客観的に構造化。横山市長の政策・予算進捗、議員質疑の4軸分析、賛否が分かれた議案ログを一次情報原本で確認できるオープンデータ基盤。",
        "image": "https://gikai-mikata.jp/ogp-osaka.png",
        "url": "https://gikai-mikata.jp/osaka/"
    },
    "nagoya": {
        "name": "名古屋市会",
        "title": "名古屋市会 議会のミカタ ｜ AIは入口。判断するのは市民です。",
        "desc": "名古屋市会公式会議録と議決データを客観的に構造化。広沢市長の政策・予算進捗、議員質疑の4軸分析、賛否が分かれた議案ログを一次情報原本で確認できるオープンデータ基盤。",
        "image": "https://gikai-mikata.jp/ogp-nagoya.png",
        "url": "https://gikai-mikata.jp/nagoya/"
    },
    "yokohama": {
        "name": "横浜市会",
        "title": "横浜市会 議会のミカタ ｜ AIは入口。判断するのは市民です。",
        "desc": "横浜市会公式会議録と議決データを客観的に構造化。原澤市長の政策・予算進捗、議員質疑の4軸分析、賛否が分かれた議案ログを一次情報原本で確認できるオープンデータ基盤。",
        "image": "https://gikai-mikata.jp/ogp-yokohama.png",
        "url": "https://gikai-mikata.jp/yokohama/"
    }
}

def generate_city_html():
    base_html = INDEX_HTML.read_text(encoding="utf-8")
    for code, meta in CITIES.items():
        city_dir = PUBLIC / code
        city_dir.mkdir(parents=True, exist_ok=True)
        out_html_path = city_dir / "index.html"

        city_html = base_html
        # title
        city_html = re.sub(r'<title>.*?</title>', f'<title>{meta["title"]}</title>', city_html)
        city_html = re.sub(r'<meta\s+property="og:title"\s+content="[^"]*"', f'<meta property="og:title" content="{meta["title"]}"', city_html)
        city_html = re.sub(r'<meta\s+name="twitter:title"\s+content="[^"]*"', f'<meta name="twitter:title" content="{meta["title"]}"', city_html)
        
        # description
        city_html = re.sub(r'<meta\s+name="description"\s+content="[^"]*"', f'<meta name="description" content="{meta["desc"]}"', city_html)
        city_html = re.sub(r'<meta\s+property="og:description"\s+content="[^"]*"', f'<meta property="og:description" content="{meta["desc"]}"', city_html)
        city_html = re.sub(r'<meta\s+name="twitter:description"\s+content="[^"]*"', f'<meta name="twitter:description" content="{meta["desc"]}"', city_html)
        
        # image
        city_html = re.sub(r'<meta\s+property="og:image"\s+content="[^"]*"', f'<meta property="og:image" content="{meta["image"]}"', city_html)
        city_html = re.sub(r'<meta\s+name="twitter:image"\s+content="[^"]*"', f'<meta name="twitter:image" content="{meta["image"]}"', city_html)
        
        # url
        city_html = re.sub(r'<meta\s+property="og:url"\s+content="[^"]*"', f'<meta property="og:url" content="{meta["url"]}"', city_html)

        out_html_path.write_text(city_html, encoding="utf-8")
        print(f"  * 生成: {out_html_path.relative_to(ROOT)} ({meta['name']}) -> {meta['image']}")

if __name__ == "__main__":
    generate_city_html()
