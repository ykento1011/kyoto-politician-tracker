import os
import re
import sys
import json
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    for env_path in [Path(".env"), Path("data-pipeline/.env")]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

CITY_CONFIGS = {
    "nagoya": {
        "city_name": "名古屋市",
        "domain": "city.nagoya.jp",
        "allowed_domains": ["city.nagoya.jp", "ssp.kaigiroku.net"],
        "blacklist_prefixes": [
            "https://www.city.nagoya.jp/zaisei",
            "https://www.city.nagoya.jp/mayor/press",
            "https://www.city.nagoya.jp/shikai/shingi",
            "https://www.city.nagoya.jp/shikai",
            "https://www.city.nagoya.jp/mayor",
            "https://www.city.nagoya.jp/shisei/keikaku",
            "https://www.city.nagoya.jp/shisei/senkyo"
        ]
    },
    "osaka": {
        "city_name": "大阪市",
        "domain": "city.osaka.lg.jp",
        "allowed_domains": ["city.osaka.lg.jp", "ssp.kaigiroku.net"],
        "blacklist_prefixes": [
            "https://www.city.osaka.lg.jp/zaisei",
            "https://www.city.osaka.lg.jp/shikai"
        ]
    },
    "kyoto": {
        "city_name": "京都市",
        "domain": "city.kyoto.lg.jp",
        "allowed_domains": ["city.kyoto.lg.jp", "ssp.kaigiroku.net"],
        "blacklist_prefixes": [
            "https://www.city.kyoto.lg.jp/gyozai",
            "https://www.city.kyoto.lg.jp/shikai"
        ]
    }
}

REDIRECT_HOSTS = {
    "vertexaisearch.cloud.google.com",
    "www.google.com",
    "google.com"
}

class MunicipalSourceResearcher:
    def __init__(self, city_code="nagoya"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません。")
        self.client = genai.Client(api_key=api_key)
        self.city_code = city_code
        self.config = CITY_CONFIGS.get(city_code, CITY_CONFIGS["nagoya"])
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MunicipalDocResearcher/1.0"
        }

    def is_deep_link(self, url: str) -> bool:
        """親ディレクトリや一覧トップではない個別公文書リンクかを厳密に判定"""
        parsed = urlparse(url)
        clean_path = parsed.path.rstrip("/")
        clean_url = f"{parsed.scheme}://{parsed.netloc}{clean_path}"

        # 1. ブラックリスト（親階層トップ）判定
        for bl in self.config.get("blacklist_prefixes", []):
            if clean_url == bl.rstrip("/"):
                return False

        # 2. 会議録システムの場合（個別閲覧画面か）
        if "ssp.kaigiroku.net" in parsed.netloc:
            if "MinuteView.html" in parsed.path or "council_id=" in url:
                return True
            return False

        # 3. 自治体サイトの場合
        if parsed.path.endswith(".html") or parsed.path.endswith(".pdf"):
            if parsed.path.endswith("/index.html") and len(parsed.path.strip("/").split("/")) <= 2:
                return False
            segments = [s for s in parsed.path.strip("/").split("/") if s]
            if len(segments) >= 3 or re.search(r"\d{4,}", parsed.path) or parsed.path.endswith(".pdf"):
                return True

        return False

    def verify_and_resolve_url(self, raw_url: str) -> tuple:
        """リダイレクトを追跡し、実在性とディープリンク要件を判定"""
        try:
            parsed = urlparse(raw_url)
            is_redirect_proxy = parsed.netloc in REDIRECT_HOSTS

            if not is_redirect_proxy:
                if not any(dom in parsed.netloc for dom in self.config["allowed_domains"]):
                    return False, raw_url, f"ドメイン不一致 ({parsed.netloc})"

            # HTTPリクエストで追跡（Googleのリダイレクトプロキシも追跡）
            res = requests.get(raw_url, headers=self.headers, timeout=12, allow_redirects=True)
            if res.status_code != 200:
                return False, raw_url, f"HTTP ステータス {res.status_code}"

            final_url = res.url
            final_parsed = urlparse(final_url)

            # 最終着地先ドメイン確認
            if not any(dom in final_parsed.netloc for dom in self.config["allowed_domains"]):
                return False, final_url, f"着地先が他ドメイン ({final_parsed.netloc})"

            # ディープリンク要件確認
            if not self.is_deep_link(final_url):
                return False, final_url, f"親階層または一覧ページ ({final_url})"

            if len(res.content) < 500:
                return False, final_url, "コンテンツ長不足 (Not Found疑い)"

            return True, final_url, "OK"

        except Exception as e:
            return False, raw_url, f"通信例外: {e}"

    def search_primary_source(self, title: str, context_hint: str = "") -> dict:
        """指定された施策や議案の一次公文書パーマリンクを探索"""
        domain = self.config["domain"]
        city_name = self.config["city_name"]

        prompt = f"""
あなたは自治体公文書調査のスペシャリストです。
{city_name}（公式ドメイン: {domain}）における以下の施策または議案について、
公式サイト上に実在する「個別記事ページ（.html）」または「公式刊行PDF（.pdf）」の完全なパーマリンクURLを探索してください。

【調査対象】
- 施策/議案名: {title}
- 背景・キーワード: {context_hint}

【検索指示】
Google検索を行う際は、必ず "site:{domain}" または "site:ssp.kaigiroku.net" を含めて精密検索してください。

【厳格ルール】
1. 局トップ（例: /zaisei/）や広報・審議一覧（例: /mayor/press/、/shikai/shingi/）などの親階層URLは一切禁止。
2. 必ず個別記事IDや文書番号を含む完全なパーマリンクURL（末尾が .html または .pdf）をテキスト内に直接記載してください。
3. 出力フォーマット:
URL: <https://から始まる完全なURL>
文書名: <特定した公文書や記事の正確なタイトル>
概要: <資料の内容要約>
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    temperature=0.1
                )
            )

            text = response.text or ""
            candidate_urls = []

            # 1. Grounding メタデータからURLを全探索
            try:
                candidate = response.candidates[0]
                if candidate.grounding_metadata:
                    g_meta = candidate.grounding_metadata
                    # chunks から取得
                    if hasattr(g_meta, "grounding_chunks") and g_meta.grounding_chunks:
                        for chunk in g_meta.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web:
                                uri = getattr(chunk.web, "uri", None)
                                if uri:
                                    candidate_urls.append(uri)
            except Exception:
                pass

            # 2. テキスト中からURLを正規表現で抽出
            found_urls = re.findall(r"https?://[a-zA-Z0-9_\-\.\/\?\#\=\&\%\+\@]+", text)
            candidate_urls.extend(found_urls)

            # 重複排除
            seen = set()
            unique_candidates = []
            for u in candidate_urls:
                u_clean = u.rstrip(".,;)")
                if u_clean not in seen:
                    seen.add(u_clean)
                    unique_candidates.append(u_clean)

            verified_target = None
            verification_log = []

            for u in unique_candidates:
                ok, final_url, reason = self.verify_and_resolve_url(u)
                verification_log.append(f"{u[:65]}... -> {'OK: ' + final_url if ok else reason}")
                if ok and not verified_target:
                    verified_target = final_url

            # 文書名・概要抽出
            doc_name = ""
            m_name = re.search(r"文書名:\s*(.+)", text)
            if m_name: doc_name = m_name.group(1).strip()

            summary = ""
            m_sum = re.search(r"概要:\s*(.+)", text)
            if m_sum: summary = m_sum.group(1).strip()

            return {
                "title": title,
                "verified_url": verified_target,
                "doc_name": doc_name,
                "summary": summary,
                "success": bool(verified_target),
                "log": verification_log,
                "raw_text": text
            }

        except Exception as e:
            return {
                "title": title,
                "verified_url": None,
                "doc_name": "",
                "summary": "",
                "success": False,
                "log": [f"API例外: {e}"],
                "raw_text": ""
            }

print("=== 1. data-pipeline/deep_research_sources.py を生成完了 ===")
p_out = Path("data-pipeline/deep_research_sources.py")
p_out.parent.mkdir(parents=True, exist_ok=True)
p_out.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

print("\n=== 2. 自動探索テストを実行（名古屋：特別職報酬審議会 諮問資料） ===")
researcher = MunicipalSourceResearcher(city_code="nagoya")
res = researcher.search_primary_source(
    title="名古屋市特別職報酬審議会への市長諮問",
    context_hint="2024年12月20日開催 市長給料減額 退職手当不支給 諮問書 開催結果 総務局"
)

print(f"結果判定: {'✅ 成功 (ディープリンク特定)' if res['success'] else '❌ 失敗'}")
print(f"確定URL: {res['verified_url']}")
print(f"文書名:   {res['doc_name']}")
print("検証ログ:")
for l in res["log"]:
    print(f"  * {l}")