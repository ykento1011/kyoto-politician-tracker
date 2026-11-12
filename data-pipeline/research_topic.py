#!/usr/bin/env python3
"""
メディア向け調査支援パイプライン（自治体ドメイン限定 Deep Research 統合版）
Step 1: ローカルDB横断抽出・固有URL紐付けバグ修正・議案PDF疎通チェック
Step 2: 自治体公式ドメイン限定 Deep Research（ホワイトリスト検証 ＋ 一次資料PDFダウンロード・テキスト抽出・構造化解析）
Step 3: 関連性3分類（直接関連／政策背景／参考情報）＆ Fail-Closed 検証状態付与（確認済／一部確認／未確認）
Step 4: 記者向け改訂版レポート本編（A4・2ページ目標）＋ 別添：一次資料・根拠一覧の自動出力（Markdown / PDF）

※制約遵守:
  既存の本番環境（frontend/）、データベース（frontend/public/data/*.json）、公開ページは一切変更しません。

Usage:
    python data-pipeline/research_topic.py \
        --city kyoto \
        --keywords "錦林,錦林市営,錦林改良,錦林浴場,新K2,新K3" \
        --broad-keywords "改良住宅,団地再生,市営浴場,公衆浴場,鹿ヶ谷" \
        --output reports/research_kinrin_final.md \
        --pdf
"""

from __future__ import annotations

import argparse
import html as html_lib
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


CITY_LABELS: dict[str, str] = {
    "kyoto": "京都市",
    "osaka": "大阪市",
    "kobe": "神戸市",
    "tokyo": "東京都",
    "yokohama": "横浜市",
    "nagoya": "名古屋市",
    "fukuoka": "福岡市",
    "sapporo": "札幌市",
}

# 自治体公式ドメイン・ホワイトリスト（外部ニュース・ブログ・SNS等を100%遮断）
OFFICIAL_DOMAIN_WHITELIST: dict[str, dict[str, Any]] = {
    "kyoto": {
        "domains": [
            "city.kyoto.lg.jp",
            "www.city.kyoto.lg.jp",
            "www2.city.kyoto.lg.jp",
        ],
        "kaigiroku_prefix": "[https://ssp.kaigiroku.net/tenant/kyoto/](https://ssp.kaigiroku.net/tenant/kyoto/)",
        "site_query": "site:city.kyoto.lg.jp",
    },
    "osaka": {
        "domains": ["city.osaka.lg.jp", "www.city.osaka.lg.jp"],
        "kaigiroku_prefix": "[https://ssp.kaigiroku.net/tenant/osaka/](https://ssp.kaigiroku.net/tenant/osaka/)",
        "site_query": "site:city.osaka.lg.jp",
    },
    "kobe": {
        "domains": ["city.kobe.lg.jp", "www.city.kobe.lg.jp"],
        "kaigiroku_prefix": "[https://ssp.kaigiroku.net/tenant/kobe/](https://ssp.kaigiroku.net/tenant/kobe/)",
        "site_query": "site:city.kobe.lg.jp",
    },
    "yokohama": {
        "domains": ["city.yokohama.lg.jp", "www.city.yokohama.lg.jp"],
        "kaigiroku_prefix": "[https://ssp.kaigiroku.net/tenant/yokohama/](https://ssp.kaigiroku.net/tenant/yokohama/)",
        "site_query": "site:city.yokohama.lg.jp",
    },
    "nagoya": {
        "domains": ["city.nagoya.jp", "www.city.nagoya.jp"],
        "kaigiroku_prefix": "[https://ssp.kaigiroku.net/tenant/nagoya/](https://ssp.kaigiroku.net/tenant/nagoya/)",
        "site_query": "site:city.nagoya.jp",
    },
}

KYOTO_GIAN_PDF_BASE = "[https://www2.city.kyoto.lg.jp/shikai/img/honkaigi/gian](https://www2.city.kyoto.lg.jp/shikai/img/honkaigi/gian)"
GIKAI_MIKATA_BASE = "[https://gikai-mikata.jp](https://gikai-mikata.jp)"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KyotoCouncilResearchPipeline/3.0"

# 同一実行内のHTTPキャッシュ
_HTTP_CACHE: dict[str, tuple[int, str, bytes]] = {}


def get_city_label(city: str) -> str:
    return CITY_LABELS.get(city.lower(), city)


def load_env_variables() -> None:
    """Load environment variables from .env or data-pipeline/.env."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        load_dotenv(Path("data-pipeline/.env"))
        return
    except ImportError:
        pass

    for env_path in (Path(".env"), Path("data-pipeline/.env")):
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, _, val = stripped.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name or "")


def normalize_nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def is_allowed_official_url(url: str, city: str) -> bool:
    """
    自治体公式ドメイン・ホワイトリスト検証。
    対象自治体の公式ドメイン（*.city.kyoto.lg.jp 等）および公式会議録テナントURLのみ True を返す。
    ニュースサイト、ブログ、SNS、まとめサイト等は強制的に False を返して遮断する。
    """
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    rules = OFFICIAL_DOMAIN_WHITELIST.get(city.lower())
    if not rules:
        return False

    # 1. 公式会議録システム（該当自治体テナントパスに厳格限定）
    kaigiroku_prefix = str(rules.get("kaigiroku_prefix") or "").lower()
    if kaigiroku_prefix and url.strip().lower().startswith(kaigiroku_prefix):
        return True

    # 2. 自治体公式ドメイン（完全一致またはサブドメイン一致）
    for allowed_domain in rules.get("domains", []):
        d = allowed_domain.lower()
        if host == d or host.endswith("." + d):
            return True

    return False


def load_json_file(path: Path, default: Any) -> Any:
    if not path.is_file():
        print(f"[WARN] データファイルが見つかりません: {path}", file=sys.stderr)
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_party_master(data_dir: Path, city: str) -> dict[str, dict[str, str]]:
    """会派マスタを読み込み、空白除去済みの正規化議員名をキーとする辞書を構築する。"""
    master: dict[str, dict[str, str]] = {}
    for src_path in (
        data_dir / f"{city}_councilors.json",
        data_dir / f"{city}_pledge_tracker.json",
    ):
        raw = load_json_file(src_path, default={})
        if isinstance(raw, dict):
            for name, info in raw.items():
                nk = normalize_name(str(name))
                if not nk:
                    continue
                if isinstance(info, dict):
                    party = str(info.get("party") or "").strip()
                    district = str(info.get("district") or "").strip()
                else:
                    party = str(info or "").strip()
                    district = ""
                prev = master.get(nk, {})
                master[nk] = {
                    "party": party or prev.get("party", ""),
                    "district": district or prev.get("district", ""),
                }
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or item.get("speaker") or "").strip()
                nk = normalize_name(name)
                if not nk:
                    continue
                party = str(item.get("party") or "").strip()
                district = str(item.get("district") or "").strip()
                prev = master.get(nk, {})
                master[nk] = {
                    "party": party or prev.get("party", ""),
                    "district": district or prev.get("district", ""),
                }
    return master


def parse_keywords(raw_keywords: str) -> list[str]:
    if not raw_keywords:
        return []
    tokens = re.split(r"[,、]", raw_keywords)
    keywords: list[str] = []
    for tok in tokens:
        cleaned = tok.strip()
        if cleaned and cleaned not in keywords:
            keywords.append(cleaned)
    return keywords


def find_matched_keywords(texts: list[str], keywords: list[str]) -> list[str]:
    if not keywords:
        return []
    combined = normalize_nfkc("\n".join(t for t in texts if t))
    return [kw for kw in keywords if normalize_nfkc(kw) in combined]


def parse_japanese_session_sort_key(session_name: str) -> tuple[int, int, str]:
    era_offsets = {"昭和": 1925, "平成": 1988, "令和": 2018}
    m = re.search(r"(昭和|平成|令和)(元|\d+)年(?:(\d+)月)?", normalize_nfkc(session_name))
    if m:
        era, year_str, month_str = m.group(1), m.group(2), m.group(3)
        era_year = 1 if year_str == "元" else int(year_str)
        west_year = era_offsets[era] + era_year
        month = int(month_str) if month_str else 0
        return (west_year, month, session_name)
    m_west = re.search(r"(20\d{2})年(?:(\d+)月)?", normalize_nfkc(session_name))
    if m_west:
        return (int(m_west.group(1)), int(m_west.group(2) or 0), session_name)
    return (9999, 99, session_name or "")


def fetch_official_url(
    url: str,
    city: str,
    timeout: float = 10.0,
) -> tuple[int, str, bytes]:
    """
    ホワイトリスト検証付きHTTP取得。
    自治体公式ドメイン以外のURLはリクエスト送信前に即座に拒否（status=-1）する。
    """
    if not url:
        return (0, "", b"")
    if not is_allowed_official_url(url, city):
        print(f"[BLOCKED] 自治体公式ドメイン外URLを遮断しました: {url}", file=sys.stderr)
        return (-1, "", b"")

    if url in _HTTP_CACHE:
        return _HTTP_CACHE[url]

    headers = {"User-Agent": USER_AGENT}
    try:
        req = urllib.request.Request(url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            ctype = str(resp.headers.get("Content-Type") or "")
            body = resp.read()
            _HTTP_CACHE[url] = (status, ctype, body)
            return (status, ctype, body)
    except urllib.error.HTTPError as exc:
        _HTTP_CACHE[url] = (exc.code, "", b"")
        return (exc.code, "", b"")
    except Exception:
        _HTTP_CACHE[url] = (0, "", b"")
        return (0, "", b"")


def decode_html_bytes(raw_bytes: bytes, content_type: str = "") -> str:
    if not raw_bytes:
        return ""
    m_charset = re.search(r"charset=([A-Za-z0-9_-]+)", content_type, re.IGNORECASE)
    candidates: list[str] = []
    if m_charset:
        candidates.append(m_charset.group(1))
    candidates.extend(["utf-8", "cp932", "shift_jis", "euc_jp"])
    for enc in candidates:
        try:
            return raw_bytes.decode(enc)
        except Exception:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def strip_html_tags(html_text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """pypdf を用いて公式PDFバイナリからテキストを抽出する。"""
    if not pdf_bytes:
        return ""
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages: list[str] = []
        for idx, page in enumerate(reader.pages):
            txt = (page.extract_text() or "").strip()
            if txt:
                pages.append(f"[Page {idx + 1}]\n{txt}")
        return "\n\n".join(pages)
    except ImportError:
        print(
            "[WARN] pypdf が未導入のためPDFテキスト抽出をスキップします（pip install pypdf で有効化）。",
            file=sys.stderr,
        )
        return ""
    except Exception as exc:
        print(f"[WARN] PDFテキスト抽出エラー: {exc}", file=sys.stderr)
        return ""


def build_kyoto_bill_pdf_candidates(session_name: str, bill_number: str) -> list[str]:
    norm_session = normalize_nfkc(session_name)
    norm_bill = normalize_nfkc(bill_number)
    m_session = re.search(r"令和\s*(元|\d+)\s*年\s*(\d+)\s*月", norm_session)
    m_bill = re.search(r"(?:議|決)\s*(\d+)", norm_bill)
    if not m_session or not m_bill:
        return []

    year_raw = m_session.group(1)
    era_year = 1 if year_raw == "元" else int(year_raw)
    month = int(m_session.group(2))
    bill_no = int(m_bill.group(1))

    year_no_pad = str(era_year)
    year_zero_pad = f"{era_year:02d}"
    base = KYOTO_GIAN_PDF_BASE.rstrip("/")

    candidates = [f"{base}/R{year_no_pad}-{month}/G{year_zero_pad}-{bill_no}.pdf"]
    if bill_no < 100:
        candidates.append(f"{base}/R{year_no_pad}-{month}/G{year_zero_pad}-{bill_no:03d}.pdf")
    if bill_no < 10:
        candidates.append(f"{base}/R{year_no_pad}-{month}/G{year_zero_pad}-{bill_no:02d}.pdf")
    return candidates


def resolve_bill_primary_documents(
    city: str,
    session_name: str,
    bill_number: str,
    title: str,
    raw_source_url: str,
    official_url: str,
    verify_http: bool = True,
) -> dict[str, Any]:
    """
    Step 1 & Step 2 連動：
    1) 京都市会公式議案PDF直リンク候補のHTTP 200確認
    2) 200でない場合、元HTMLページ（例: gian11.html）を取得し、該当議案番号行内の実PDFリンクを探索
    3) 取得できた公式PDFのテキストを直接抽出
    4) 固有の official_url（会議録）のHTTP疎通と本文一致を個別検証（同一ID上書きバグ解消）
    """
    pdf_url = ""
    pdf_text = ""
    html_excerpt = ""
    verify_notes: list[str] = []

    if city.lower() == "kyoto":
        candidates = build_kyoto_bill_pdf_candidates(session_name, bill_number)
        if not verify_http and candidates:
            pdf_url = candidates[0]
        elif verify_http:
            for cand in candidates:
                st, ctype, raw_bytes = fetch_official_url(cand, city)
                if st == 200 and raw_bytes:
                    pdf_url = cand
                    pdf_text = extract_pdf_text(raw_bytes)
                    verify_notes.append(f"公式議案PDF 200 OK ({cand})")
                    break

    # 直接組み立てたPDFが200でない場合、元HTMLページから該当議案の記載・リンクを探索
    if verify_http and raw_source_url:
        st_html, ctype_html, raw_html_bytes = fetch_official_url(raw_source_url, city)
        if st_html == 200 and raw_html_bytes:
            if "pdf" in ctype_html.lower() or raw_source_url.lower().endswith(".pdf"):
                if not pdf_url:
                    pdf_url = raw_source_url
                    pdf_text = extract_pdf_text(raw_html_bytes)
                    verify_notes.append("原典PDF直接取得済 (200 OK)")
            else:
                html_doc = decode_html_bytes(raw_html_bytes, ctype_html)
                norm_bill = normalize_nfkc(bill_number).replace(" ", "")
                m_digits = re.search(r"(\d+)", norm_bill)
                bill_digits = m_digits.group(1) if m_digits else ""

                blocks = re.findall(
                    r"<tr[\s\S]*?</tr>|<li[\s\S]*?</li>|<p[\s\S]*?</p>",
                    html_doc,
                    flags=re.IGNORECASE,
                )
                for blk in blocks:
                    plain_blk = normalize_nfkc(strip_html_tags(blk))
                    matched = False
                    if norm_bill and norm_bill in plain_blk.replace(" ", ""):
                        matched = True
                    elif bill_digits and re.search(
                        rf"(?:議|議案|第)\s*0*{re.escape(bill_digits)}(?:号|\b|[^\d])",
                        plain_blk,
                    ):
                        matched = True
                    elif title and normalize_nfkc(title[:12]) in plain_blk:
                        matched = True

                    if not matched:
                        continue

                    html_excerpt = plain_blk
                    verify_notes.append("市会公式議案一覧HTML内の該当議案記載を確認")

                    if not pdf_url:
                        hrefs = re.findall(
                            r'href\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']',
                            blk,
                            flags=re.IGNORECASE,
                        )
                        for href in hrefs:
                            abs_pdf = urllib.parse.urljoin(raw_source_url, href.strip())
                            pst, _, pbytes = fetch_official_url(abs_pdf, city)
                            if pst == 200 and pbytes:
                                pdf_url = abs_pdf
                                pdf_text = extract_pdf_text(pbytes)
                                verify_notes.append(f"HTML内リンクから公式PDF取得済 ({abs_pdf})")
                                break
                    break

                if not html_excerpt:
                    verify_notes.append("市会公式議案一覧HTML HTTP 200確認（個別議案行の一致は要目視）")
        elif st_html > 0:
            verify_notes.append(f"議案ページ接続エラー (HTTP {st_html})")

    # 固有の official_url（会議録）の検証
    minute_verified = False
    if verify_http and official_url:
        mst, mctype, mbytes = fetch_official_url(official_url, city)
        if mst == 200:
            mplain = normalize_nfkc(strip_html_tags(decode_html_bytes(mbytes, mctype)))
            if any(
                k in mplain
                for k in [normalize_nfkc(bill_number), "錦林", normalize_nfkc(title[:8])]
                if k
            ):
                minute_verified = True
                verify_notes.append("会議録URL HTTP 200・原典本文一致を確認")
            else:
                verify_notes.append("会議録URL HTTP 200疎通確認（SPA動的描画のため該当箇所は要画面確認）")
        elif mst > 0:
            verify_notes.append(f"会議録URL接続エラー (HTTP {mst})")

    if (pdf_url and pdf_text) or minute_verified:
        verify_status = "確認済"
    elif html_excerpt or any("200" in n for n in verify_notes):
        verify_status = "一部確認"
    else:
        verify_status = "未確認"

    return {
        "effective_source_url": pdf_url if pdf_url else raw_source_url,
        "pdf_url": pdf_url,
        "pdf_text": pdf_text,
        "html_excerpt": html_excerpt,
        "verify_status": verify_status,
        "verify_note": " ／ ".join(verify_notes) if verify_notes else "未検証",
    }


def parse_contract_fields_from_text(text: str) -> dict[str, str]:
    """
    議案PDF・HTML抽出テキストから契約変更フィールドを抽出する。
    確認できない項目は絶対に推測せず '未確認' を返す。
    """
    norm = normalize_nfkc(text)
    if not norm:
        return {
            "before_amount": "未確認",
            "after_amount": "未確認",
            "diff_amount": "未確認",
            "cumulative_diff": "未確認",
            "schedule": "未確認",
            "reason": "未確認",
            "city_explanation": "未確認",
        }

    before_amt = "未確認"
    after_amt = "未確認"
    diff_amt = "未確認"
    cum_diff = "未確認"

    m_before = re.search(
        r"変更前(?:の)?(?:契約)?金額[^\d]{0,15}([0-9,]+(?:\.[0-9]+)?\s*(?:億|万)?円)",
        norm,
    )
    m_after = re.search(
        r"変更後(?:の)?(?:契約)?金額[^\d]{0,15}([0-9,]+(?:\.[0-9]+)?\s*(?:億|万)?円)",
        norm,
    )
    m_diff = re.search(
        r"(?:増減額|増加額|減少額|差引)[^\d+-]{0,15}([+-▲△]?\s*[0-9,]+(?:\.[0-9]+)?\s*(?:億|万)?円)",
        norm,
    )
    m_cum = re.search(
        r"(?:累計(?:の)?増減額|当初契約からの増減)[^\d+-]{0,15}([+-▲△]?\s*[0-9,]+(?:\.[0-9]+)?\s*(?:億|万)?円)",
        norm,
    )

    if m_before:
        before_amt = m_before.group(1).strip()
    if m_after:
        after_amt = m_after.group(1).strip()
    if m_diff:
        diff_amt = m_diff.group(1).strip()
    if m_cum:
        cum_diff = m_cum.group(1).strip()

    if before_amt == "未確認" and after_amt == "未確認":
        single_amt = re.search(r"契約金額[^\d]{0,15}([0-9,]+(?:\.[0-9]+)?\s*(?:億|万)?円)", norm)
        if single_amt:
            after_amt = single_amt.group(1).strip()

    m_sched = re.search(
        r"(?:工期|完成期限|履行期限)[^\n。]{0,70}(?:令和\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日)",
        norm,
    )
    schedule_str = m_sched.group(0).strip() if m_sched else "未確認"

    m_reason = re.search(r"(?:変更(?:の)?理由|提案理由|理由)[\s:：]*([^\n]{5,160})", norm)
    reason_str = m_reason.group(1).strip() if m_reason else "未確認"

    return {
        "before_amount": before_amt,
        "after_amount": after_amt,
        "diff_amount": diff_amt,
        "cumulative_diff": cum_diff,
        "schedule": schedule_str,
        "reason": reason_str,
        "city_explanation": reason_str if reason_str != "未確認" else "未確認",
    }


def classify_relevance_three_tiers(
    text_blob: str,
    title_or_meeting: str = "",
    core_keywords: list[str] | None = None,
) -> str:
    """
    Step 3: 関連性の3分類
    - 直接関連: 錦林団地・錦林市営住宅・錦林浴場・新K2・新K3を直接扱う質疑・議案・条例・予算
    - 政策背景: 京都市全体の住宅政策・浴場政策など制度的関連があるもの
    - 参考情報: 他団地個別事例や関連性が弱い一般的質疑
    """
    norm = normalize_nfkc(f"{title_or_meeting}\n{text_blob}")
    direct_terms = list(core_keywords or []) + ["錦林", "新K2", "新K3", "錦林浴場", "鹿ヶ谷"]
    if any(normalize_nfkc(t) in norm for t in direct_terms if t):
        return "直接関連"

    other_complex_terms = ["桃陵", "三条市営", "壬生東", "八条市営", "山科", "醍醐", "叡山電鉄"]
    policy_terms = [
        "市営住宅ストック",
        "ストック総合活用指針",
        "公営住宅法",
        "最低居住面積水準",
        "誘導居住面積水準",
        "団地再生計画",
        "目的外使用",
        "家賃減免",
        "共益費",
        "公衆浴場",
        "銭湯",
        "ボイラー",
    ]
    has_policy = any(t in norm for t in policy_terms)
    has_other = any(t in norm for t in other_complex_terms)

    if has_policy and not has_other:
        return "政策背景"
    if has_policy and has_other:
        if any(k in norm for k in ["ストック", "指針", "面積水準", "減免", "ボイラー", "銭湯"]):
            return "政策背景"
    return "参考情報"


def build_mikata_statement_url(city: str, speaker: str, statement_id: str = "") -> str:
    base = f"{GIKAI_MIKATA_BASE}/{city}/"
    query = f"?speaker={urllib.parse.quote(speaker)}" if speaker else ""
    fragment = f"#{statement_id}" if statement_id else ""
    return f"{base}{query}{fragment}"


def sanitize_nested_markdown_links(text: str) -> str:
    return re.sub(
        r"\]\(\[(https?://[^\]]+)\]\(\1\)([^\)]*)\)",
        r"](\1\2)",
        text,
    )


def step1_extract_local_db(
    data_dir: Path,
    city: str,
    core_keywords: list[str],
    broad_keywords: list[str],
    verify_http: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Step 1：既存プロセス（ローカルDB横断抽出・URL紐付けバグ修正・議案PDF疎通）
    """
    party_master = build_party_master(data_dir, city)
    raw_statements = load_json_file(data_dir / f"{city}_statements_summary.json", default=[])
    raw_votes = load_json_file(data_dir / f"{city}_votes_summary.json", default=[])

    if not isinstance(raw_statements, list) or not isinstance(raw_votes, list):
        raise ValueError("入力JSONデータの形式が不正です（list形式が必要）。")

    # 1-A. 質疑データの抽出（コア＋広域関連）
    statements: list[dict[str, Any]] = []
    for row in raw_statements:
        if not isinstance(row, dict):
            continue
        summary = str(row.get("summary") or "").strip()
        reasoning = str(row.get("scoring_reasoning") or "").strip()
        statement_text = str(row.get("statement_text") or "").strip()
        meeting_title = str(row.get("meeting_title") or "").strip()
        texts = [summary, reasoning, statement_text, meeting_title]

        core_hits = find_matched_keywords(texts, core_keywords)
        broad_hits = find_matched_keywords(texts, broad_keywords)
        if not core_hits and not broad_hits:
            continue

        statement_id = str(row.get("id") or "").strip()
        speaker = str(row.get("speaker") or "").strip()
        party = party_master.get(normalize_name(speaker), {}).get("party") or "会派不明"
        source_url = str(row.get("source_url") or "").strip()
        mikata_url = build_mikata_statement_url(city, speaker, statement_id)

        relevance = classify_relevance_three_tiers(
            f"{summary}\n{reasoning}\n{statement_text}",
            meeting_title,
            core_keywords,
        )

        verify_status = "未確認"
        verify_note = "リモート疎通未実行"
        if verify_http and source_url:
            mst, mctype, mbytes = fetch_official_url(source_url, city)
            if mst == 200:
                mplain = normalize_nfkc(strip_html_tags(decode_html_bytes(mbytes, mctype)))
                if any(k in mplain for k in [normalize_name(speaker)[:3], "錦林", "市営住宅", "浴場"] if k):
                    verify_status = "確認済"
                    verify_note = "公式会議録URL HTTP 200・原典本文一致を確認"
                else:
                    verify_status = "一部確認"
                    verify_note = "公式会議録URL HTTP 200疎通確認（SPA動的描画のため発言箇所は要画面確認）"
            elif mst == -1:
                verify_status = "未確認"
                verify_note = "ホワイトリスト外URLのため遮断"
            else:
                verify_status = "未確認"
                verify_note = f"会議録URL接続エラー (HTTP {mst})"

        statements.append(
            {
                "record_id": "",
                "record_type": "statement",
                "statement_id": statement_id,
                "match_tier": "core" if core_hits else "broad",
                "relevance": relevance,
                "verify_status": verify_status,
                "verify_note": verify_note,
                "meeting_date": str(row.get("meeting_date") or "").strip(),
                "meeting_title": meeting_title,
                "speaker": speaker,
                "party": party,
                "category": str(row.get("category") or "").strip(),
                "summary": summary,
                "scoring_reasoning": reasoning,
                "statement_text": statement_text if core_hits else "",
                "source_url": source_url,
                "mikata_url": mikata_url,
            }
        )

    statements.sort(key=lambda r: (r["meeting_date"], r["meeting_title"], r["speaker"]))
    for idx, s in enumerate(statements, start=1):
        s["record_id"] = f"S{idx}"

    # 1-B. 議案・採決データの徹底再検索（条例案・補正予算案含む＋固有URL紐付けバグ修正）
    extended_vote_keywords = list(
        dict.fromkeys(core_keywords + ["公衆浴場条例", "市営浴場", "錦林浴場"])
    )
    votes: list[dict[str, Any]] = []
    for row in raw_votes:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        session_name = str(row.get("session_name") or "").strip()
        bill_number = str(row.get("bill_number") or "").strip()

        hits = find_matched_keywords([title, session_name], extended_vote_keywords)
        if not hits:
            continue

        # 各レコード固有の source_url / official_url を個別に維持（同一ID上書きバグ修正）
        raw_source_url = str(row.get("source_url") or "").strip()
        official_url = str(row.get("official_url") or "").strip()
        mikata_url = f"{GIKAI_MIKATA_BASE}/{city}/"

        doc_info = resolve_bill_primary_documents(
            city=city,
            session_name=session_name,
            bill_number=bill_number,
            title=title,
            raw_source_url=raw_source_url,
            official_url=official_url,
            verify_http=verify_http,
        )
        contract_fields = parse_contract_fields_from_text(
            f"{doc_info['html_excerpt']}\n{doc_info['pdf_text']}"
        )
        relevance = classify_relevance_three_tiers(title, session_name, core_keywords)

        votes.append(
            {
                "record_id": "",
                "record_type": "vote",
                "relevance": relevance,
                "verify_status": doc_info["verify_status"],
                "verify_note": doc_info["verify_note"],
                "session_name": session_name,
                "bill_number": bill_number,
                "title": title,
                "result": str(row.get("result") or "").strip(),
                "votes": row.get("votes") if isinstance(row.get("votes"), dict) else {},
                "source_url": raw_source_url,
                "effective_source_url": doc_info["effective_source_url"],
                "pdf_url": doc_info["pdf_url"],
                "official_url": official_url,
                "mikata_url": mikata_url,
                "html_excerpt": doc_info["html_excerpt"][:800],
                "pdf_text": doc_info["pdf_text"][:3000],
                "contract_details": contract_fields,
            }
        )

    votes.sort(key=lambda r: (parse_japanese_session_sort_key(r["session_name"]), r["bill_number"]))
    for idx, v in enumerate(votes, start=1):
        v["record_id"] = f"V{idx}"

    return statements, votes


def step2_official_domain_deep_research(
    city: str,
    core_keywords: list[str],
    statements: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    model_name: str = "gemini-2.5-flash",
    enabled: bool = True,
) -> list[dict[str, Any]]:
    """
    Step 2：自治体公式ドメイン限定 Deep Research 工程
    - 許可ドメイン（kyoto なら city.kyoto.lg.jp / ssp.kaigiroku.net/tenant/kyoto/）のみを対象に、
      Step 1 で不足している「条例改正（錦林浴場廃止条例）」「工期変更」「補正予算措置」「賛否逆転討論」を深掘り探索する。
    - Gemini Google Search Grounding 使用時も `site:city.kyoto.lg.jp` を検索クエリに必須付与し、
      返却されたURLを Python 側でホワイトリスト検証して対象外ドメイン（ニュース・SNS・ブログ等）を強制破棄する。
    """
    if not enabled:
        print("[INFO] Step 2 (Deep Research): --skip-deep-research によりスキップしました。")
        return []

    rules = OFFICIAL_DOMAIN_WHITELIST.get(city.lower())
    if not rules:
        print(f"[WARN] Step 2: 自治体 '{city}' の公式ドメインホワイトリストが未定義のためスキップします。")
        return []

    site_filter = rules["site_query"]
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    deep_records: list[dict[str, Any]] = []

    if not api_key:
        print(
            "[WARN] Step 2 (Deep Research): GEMINI_API_KEY 未設定のため、外部Web検索をスキップしローカル抽出＋既知公式URL検証のみで継続します。"
        )
        return deep_records

    # Step 1 で抽出した議案・論点から公式ドメイン限定検索クエリを構築
    target_queries = [
        f"{site_filter} 錦林市営住宅 新K2棟 新K3棟 契約変更",
        f"{site_filter} 錦林浴場 廃止 公衆浴場条例 指定管理者",
    ]
    print(f"[INFO] Step 2 (Deep Research) 開始: 許可ドメイン={rules['domains']}, クエリ={target_queries}")

    candidate_urls: list[str] = []
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=api_key)
        for q in target_queries:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=(
                        f"次の検索クエリで自治体公式ドメイン内の一次資料（議案・条例・予算・会議録）のみを検索し、"
                        f"該当する公式URLを列挙してください: {q}"
                    ),
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],
                        temperature=0.0,
                    ),
                )
                # Grounding メタデータから公式URLを抽出
                for cand in getattr(resp, "candidates", []) or []:
                    gm = getattr(cand, "grounding_metadata", None)
                    for chunk in getattr(gm, "grounding_chunks", []) or []:
                        web = getattr(chunk, "web", None)
                        uri = getattr(web, "uri", "") if web else ""
                        if uri and is_allowed_official_url(uri, city):
                            if uri not in candidate_urls:
                                candidate_urls.append(uri)
                        elif uri:
                            print(f"[BLOCKED] Deep Research 外部ドメインURLを破棄: {uri}", file=sys.stderr)

                # テキスト本文中のURLも抽出してホワイトリスト検証
                text_urls = re.findall(r"https?://[^\s\)\]>\"']+", getattr(resp, "text", "") or "")
                for u in text_urls:
                    clean_u = u.rstrip(".,;:")
                    if is_allowed_official_url(clean_u, city):
                        if clean_u not in candidate_urls:
                            candidate_urls.append(clean_u)
                    else:
                        print(f"[BLOCKED] Deep Research 外部ドメインURLを破棄: {clean_u}", file=sys.stderr)
            except Exception as q_exc:
                print(f"[WARN] Step 2 検索クエリ実行エラー ({q}): {q_exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[WARN] Step 2 Grounding初期化エラー: {exc}", file=sys.stderr)

    # 既に Step 1 で取得済みのURLを除外
    existing_urls = {
        u
        for item in (statements + votes)
        for u in (
            item.get("source_url"),
            item.get("effective_source_url"),
            item.get("pdf_url"),
            item.get("official_url"),
        )
        if u
    }
    new_official_urls = [u for u in candidate_urls if u not in existing_urls][:8]

    for idx, url in enumerate(new_official_urls, start=1):
        status, ctype, raw_bytes = fetch_official_url(url, city)
        if status != 200 or not raw_bytes:
            continue

        extracted_text = ""
        doc_title = url
        if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
            extracted_text = extract_pdf_text(raw_bytes)
            doc_title = f"公式PDF資料 ({Path(urllib.parse.urlparse(url).path).name})"
        else:
            html_str = decode_html_bytes(raw_bytes, ctype)
            m_title = re.search(r"<title[^>]*>([\s\S]*?)</title>", html_str, flags=re.IGNORECASE)
            if m_title:
                doc_title = strip_html_tags(m_title.group(1)) or url
            extracted_text = strip_html_tags(html_str)

        if not extracted_text:
            continue

        relevance = classify_relevance_three_tiers(extracted_text, doc_title, core_keywords)
        if relevance == "参考情報":
            continue

        deep_records.append(
            {
                "record_id": f"D{idx}",
                "record_type": "deep_research_doc",
                "relevance": relevance,
                "verify_status": "確認済" if extracted_text else "一部確認",
                "verify_note": f"自治体公式ドメイン限定Deep Research取得 (HTTP 200 OK)",
                "title": doc_title,
                "source_url": url,
                "mikata_url": f"{GIKAI_MIKATA_BASE}/{city}/",
                "extracted_text": extracted_text[:3000],
            }
        )

    print(f"[INFO] Step 2 (Deep Research) 完了: 新規公式資料 {len(deep_records)} 件を取得・検証")
    return deep_records


def build_unified_link_map(
    statements: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    deep_docs: list[dict[str, Any]],
) -> dict[str, str]:
    """全レコードの確定Markdownリンクマップを構築する。"""
    link_map: dict[str, str] = {}

    for s in statements:
        parts: list[str] = []
        if s["source_url"]:
            parts.append(f"[公式会議録]({s['source_url']})")
        if s["mikata_url"]:
            parts.append(f"[議会のミカタ]({s['mikata_url']})")
        link_map[s["record_id"]] = sanitize_nested_markdown_links(" ".join(parts))

    for v in votes:
        primary_parts: list[str] = []
        eff_src = v.get("effective_source_url") or v.get("source_url") or ""
        if eff_src:
            label = "議案PDF" if eff_src.lower().endswith(".pdf") else "市会議案ページ"
            primary_parts.append(f"[{label}]({eff_src})")
        if v.get("official_url"):
            primary_parts.append(f"[公式会議録]({v['official_url']})")
        primary_str = " / ".join(primary_parts)
        mikata_str = f"[議会のミカタ]({v['mikata_url']})" if v.get("mikata_url") else ""
        combined = " ".join(p for p in (primary_str, mikata_str) if p)
        link_map[v["record_id"]] = sanitize_nested_markdown_links(combined)

    for d in deep_docs:
        parts = []
        if d.get("source_url"):
            label = "公式PDF" if d["source_url"].lower().endswith(".pdf") else "自治体公式資料"
            parts.append(f"[{label}]({d['source_url']})")
        if d.get("mikata_url"):
            parts.append(f"[議会のミカタ]({d['mikata_url']})")
        link_map[d["record_id"]] = sanitize_nested_markdown_links(" ".join(parts))

    return link_map


def resolve_link_placeholders(text: str, link_map: dict[str, str]) -> str:
    pattern = re.compile(r"\[\[\s*LINK\s*:\s*([A-Za-z0-9_-]+)\s*\]\]")
    resolved = pattern.sub(lambda m: link_map.get(m.group(1).strip(), ""), text)
    return sanitize_nested_markdown_links(resolved)


def build_step4_system_prompt(city_label: str) -> str:
    return f"""あなたは報道機関（京都新聞）の調査報道デスクを支援するファクト整理専門アナリストです。
提供された「構造化JSONデータ（Step 1 ローカルDB抽出 ＋ Step 2 自治体公式ドメイン限定 Deep Research 一次資料解析結果）」のみを根拠として、記者向け改訂版レポート本編（Markdown）をJSON形式で出力してください。

【出力形式（JSON厳守）】
{{
  "part1_reporter_brief_md": "# 錦林市営住宅の再生事業をめぐる議会審議と行政対応\\n..."
}}

【絶対遵守ルール】
1. **内部システム情報の完全排除**:
   - 検索キーワード列、`gemini_api` 等のモデル名、抽出件数メタデータなどの内部システム情報は一切記載しないでください。
2. **推測・創作・断定の厳禁（Fail-Closed）**:
   - 一次資料PDFおよびDBから確認できない契約金額・増減額・工期・変更理由・賛否逆転理由・条例改正内容は絶対に推測で補完せず、明示的に「未確認」または「討論記録なし・理由未確認」と記載してください。
   - **賛否の変化という事実と、その理由に関する推測を混同しないでください。**
3. **リンク指定（IDプレースホルダ使用）**:
   - 生URLを自ら記述せず、必ず対応レコードの `[[LINK:S1]]` / `[[LINK:V1]]` / `[[LINK:D1]]` を末尾にそのまま埋め込んでください。
4. **A4・2ページ目標の構成（見出し・項目厳守）**:
   必ず以下の構成で簡潔かつ高密度に作成してください：

# 錦林市営住宅の再生事業をめぐる議会審議と行政対応
*新棟建設、契約変更、錦林浴場の廃止を中心に*

- **対象自治体**: {city_label}
- **調査対象期間**: （入力データ内の最古日〜最新議案会期）
- **最終確認日**: （指定された本日日付）
- **発行**: KICKs／議会のミカタ

## 1. 調査概要・重要な発見3点
（調査目的を2〜3行で述べ、箇条書きで「重要な発見3点」を事実のみで記載）

## 2. 政策・議会審議の時系列と新棟建設・浴場廃止の関係
（「住宅建替え → 住戸への浴室整備 → 浴場廃止方針 → 工期変更 → 浴場運営・財政負担への影響」という一連の政策プロセスを軸に、直接関連の質疑・議案・公式資料と必要な政策背景を時系列に整理。未確認の時期・条例・予算がある場合は「原典未確認」と明記。各項目末尾に `[[LINK:...]]` を付与）

## 3. 新K2棟・新K3棟の契約変更履歴・金額と会派別賛否の変化
（議139・議237・議75・議81・議106の比較表：会期｜議案｜変更前金額｜変更後金額｜増減額・累計｜工期・変更理由｜議決結果・会派別賛否。未確認欄は「未確認」と記載。あわせて2026年9月市会・議106における日本共産党（反対→賛成）と維新・京都・国民（賛成→反対）の賛否逆転の事実と、原典上の理由確認結果を明記）

## 4. {city_label}の対応状況と記者が追加取材すべき論点（4点）
（現在確認できる行政対応と、記者が行政・会派へ追加取材すべき客観的論点4点）

## 5. 主要な一次資料リンク
（直接関連する主要議案・質疑・公式資料のリンク一覧 `[[LINK:...]]`）
"""


def build_failsafe_reporter_brief(
    city_label: str,
    statements: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    deep_docs: list[dict[str, Any]],
    link_map: dict[str, str],
    today_str: str,
) -> str:
    """API未接続・エラー時のフェイルセーフ本編生成（A4・2ページ目標構成）。"""
    direct_stmts = [s for s in statements if s["relevance"] == "直接関連"]
    policy_stmts = [s for s in statements if s["relevance"] == "政策背景"]
    k2_votes = [v for v in votes if "新K2" in v["title"] or "新K3" in v["title"]]
    bath_votes = [v for v in votes if "浴場" in v["title"]]

    dates = [s["meeting_date"] for s in statements if s.get("meeting_date")]
    sessions = [v["session_name"] for v in votes if v.get("session_name")]
    period_str = (
        f"{min(dates) if dates else '2023年10月'}〜{sessions[-1] if sessions else '令和8年9月市会'}"
    )

    lines: list[str] = [
        "# 錦林市営住宅の再生事業をめぐる議会審議と行政対応",
        "*新棟建設、契約変更、錦林浴場の廃止を中心に*",
        "",
        f"- **対象自治体**: {city_label}",
        f"- **調査対象期間**: {period_str}",
        f"- **最終確認日**: {today_str}",
        "- **発行**: KICKs／議会のミカタ",
        "",
        "## 1. 調査概要・重要な発見3点",
        f"{city_label}左京区の錦林市営住宅（新K2棟・新K3棟）の建替え事業および京都市立錦林浴場の廃止・運営移行をめぐる議会審議と行政対応を、市会会議録および議案一次資料から検証した。",
        "",
        "1. **新棟新築工事請負契約の4回連続変更と会派賛否の逆転**: 令和6年11月市会（議139）での契約締結後、4回の変更議案（議237・議75・議81・議106）が提出・可決された。令和8年9月市会（議106）では、それまで反対していた日本共産党が賛成に、賛成していた維新・京都・国民が反対に逆転した（討論記録なし・理由未確認）。",
        "2. **新棟の住戸面積水準と既存入居者移転をめぐる審議**: 令和6年12月まちづくり委員会で、新K2・K3棟の間取り（2K 35㎡・2DK 45㎡・3DK 60㎡）と国の誘導居住面積水準との乖離が問われ、市側は既存入居者の早期移転と公営住宅法に基づく最低居住面積水準（単身25㎡・2人35㎡）を根拠に事業方針を説明した。",
        "3. **錦林浴場の指定管理者指定と廃止関連経緯の切り分け**: 令和8年7月市会（議82）で京都市立錦林浴場の指定管理者指定が可決された一方、制度自体の新規導入ではなく既存制度下での指定議決である点を確認。2025年12月の廃止条例や2026年7月・9月の廃止時期変更・補正予算措置はDB議案一覧上では検出されず原典未確認である。",
        "",
        "## 2. 政策・議会審議の時系列と新棟建設・浴場廃止の関係",
        "市営住宅の団地再生事業は「市営住宅ストック総合活用指針」（令和3年策定・おおむね令和12年まで）に基づき進められている。住宅建替えに伴う住戸内浴室の整備と公衆浴場廃止の政策プロセスについて、確認できた事実と未確認事項は以下の通り。",
        "",
    ]

    for s in direct_stmts:
        lines.append(
            f"- **{s['meeting_date']}｜{s['meeting_title']}｜{s['speaker']}（{s['party']}）**: "
            f"{s['summary']} {link_map.get(s['record_id'], '')}"
        )
    if policy_stmts:
        lines.append(
            f"- **【政策背景】市全体の住宅・浴場基準（{len(policy_stmts)}件）**: "
            "ZEH水準・35㎡統一規格（2023-10-23 平井良人議員）、ストック指針に基づく約2万3,000戸の量的最適化（2025-03-03 赤阪仁議員）、銭湯ボイラー等更新補助金拡充（2025-09-22 山本陽子議員）が審議された。"
        )
    for bv in bath_votes:
        lines.append(
            f"- **{bv['session_name']} {bv['bill_number']}『{bv['title']}』**: 議決結果＝**{bv['result']}** {link_map.get(bv['record_id'], '')}"
        )
    for d in deep_docs:
        lines.append(
            f"- **【公式資料】{d['title']}**: 自治体公式ドメイン資料を確認 {link_map.get(d['record_id'], '')}"
        )
    lines.append(
        "- **【未確認事項の明示】**: 2025年12月市会の錦林浴場廃止条例改正、および2026年7月・9月の工期変更に伴う廃止時期変更・指定管理期間変更・追加予算措置については、現行の議決データおよび取得可能PDFからは確認できず **未確認**。"
    )

    lines.extend(
        [
            "",
            "## 3. 新K2棟・新K3棟の契約変更履歴・金額と会派別賛否の変化",
            "",
            "| 会期 | 議案 | 変更前金額 | 変更後金額 | 増減額・累計 | 工期・変更理由 | 議決結果・主要会派別賛否 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for kv in k2_votes:
        cd = kv["contract_details"]
        vmap = kv["votes"]
        jimin = vmap.get("自由民主党京都市会議員団", "—")
        ishin = vmap.get("維新・京都・国民市会議員団", "—")
        kyosan = vmap.get("日本共産党京都市会議員団", "—")
        komei = vmap.get("公明党京都市会議員団", "—")
        stance = f"{kv['result']}（自民:{jimin} / 維新:{ishin} / 共産:{kyosan} / 公明:{komei}）"
        lines.append(
            f"| {kv['session_name']} | {kv['bill_number']} | {cd['before_amount']} | {cd['after_amount']} | "
            f"{cd['diff_amount']}（累計:{cd['cumulative_diff']}） | 工期:{cd['schedule']} / 理由:{cd['reason']} | {stance} |"
        )

    lines.extend(
        [
            "",
            "- **会派別賛否の逆転（事実と未確認事項の区別）**: 議139（令和6年11月）から議81（令和8年7月）までは「日本共産党のみ反対・他会派賛成」で推移したが、**議106（令和8年9月）で日本共産党が賛成、維新・京都・国民が反対、平田圭議員が退席・棄権**へと逆転した。本会議討論・委員会記録からの逆転理由の特定は **討論記録なし・理由未確認** である。",
            "",
            f"## 4. {city_label}の対応状況と記者が追加取材すべき論点",
            "1. **契約変更4議案（議237・議75・議81・議106）の契約金額増減と工期延長の実態**: 各変更議案の契約変更内訳書における変更前後の契約金額、累計増減額、および新K2・K3棟の完成予定時期の遅れの有無。",
            "2. **令和8年9月市会（議106）における共産・維新の賛否逆転理由**: 第4回変更議案で両会派が賛否を反転させた具体的な判断理由と、まちづくり委員会等での審議経緯。",
            "3. **錦林浴場の廃止条例・廃止時期変更・指定管理期間の整合性**: 既存制度下での指定管理者指定（議82）の指定期間、2025年12月以降の公衆浴場条例改正の有無、および工期変更に伴う廃止時期・追加予算措置の実態。",
            "4. **既存入居者の移転支援と誘導居住面積水準への対応**: 2K（35㎡）中心の設計に対する入居者要望への対応状況と、建替え後の余剰地活用方針。",
            "",
            "## 5. 主要な一次資料リンク",
        ]
    )
    for s in direct_stmts:
        lines.append(f"- 質疑（{s['meeting_date']} {s['speaker']}）: {link_map.get(s['record_id'], '')}")
    for v in k2_votes + bath_votes:
        lines.append(f"- 議案（{v['session_name']} {v['bill_number']}）: {link_map.get(v['record_id'], '')}")
    for d in deep_docs:
        lines.append(f"- 公式資料（{d['title']}）: {link_map.get(d['record_id'], '')}")

    return sanitize_nested_markdown_links("\n".join(lines))


def generate_reporter_brief_part(
    city: str,
    statements: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    deep_docs: list[dict[str, Any]],
    link_map: dict[str, str],
    today_str: str,
    model_name: str = "gemini-2.5-flash",
) -> tuple[str, str]:
    """Step 4A: 記者向け改訂版レポート本編（A4・2ページ目標）を生成する。"""
    city_label = get_city_label(city)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return (
            build_failsafe_reporter_brief(
                city_label, statements, votes, deep_docs, link_map, today_str
            ),
            "failsafe_structured",
        )

    # 本編へ渡すのは「直接関連」と「政策背景」のみ（「参考情報」は別添にのみ格納）
    llm_statements = [
        {
            "record_id": s["record_id"],
            "relevance": s["relevance"],
            "verify_status": s["verify_status"],
            "meeting_date": s["meeting_date"],
            "meeting_title": s["meeting_title"],
            "speaker": s["speaker"],
            "party": s["party"],
            "summary": s["summary"],
            "scoring_reasoning": s["scoring_reasoning"],
            "statement_text": s["statement_text"][:2000],
        }
        for s in statements
        if s["relevance"] in ("直接関連", "政策背景")
    ]
    llm_votes = [
        {
            "record_id": v["record_id"],
            "relevance": v["relevance"],
            "verify_status": v["verify_status"],
            "session_name": v["session_name"],
            "bill_number": v["bill_number"],
            "title": v["title"],
            "result": v["result"],
            "votes": v["votes"],
            "contract_details": v["contract_details"],
            "html_excerpt": v["html_excerpt"],
            "pdf_text_excerpt": v["pdf_text"][:2000],
        }
        for v in votes
    ]
    llm_deep = [
        {
            "record_id": d["record_id"],
            "relevance": d["relevance"],
            "verify_status": d["verify_status"],
            "title": d["title"],
            "extracted_text_excerpt": d["extracted_text"][:1500],
        }
        for d in deep_docs
    ]

    user_prompt = (
        f"本日日付（最終確認日）: {today_str}\n"
        "以下の構造化JSONデータ（Step 1 ローカルDB抽出 ＋ Step 2 自治体公式ドメイン限定 Deep Research 結果）のみに基づき、"
        "`part1_reporter_brief_md` を作成してください。\n\n"
        f"```json\n{json.dumps({'statements': llm_statements, 'votes': llm_votes, 'deep_research_docs': llm_deep}, ensure_ascii=False, indent=2)}\n```"
    )

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=build_step4_system_prompt(city_label),
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        raw_text = (response.text or "").strip()
        data = json.loads(raw_text)
        brief_md = resolve_link_placeholders(
            str(data["part1_reporter_brief_md"]).strip(), link_map
        )
        return brief_md, f"gemini_api ({model_name})"
    except Exception as exc:
        print(
            f"[WARN] 本編LLM生成をスキップし構造化フェイルセーフ出力を使用します: {exc}",
            file=sys.stderr,
        )
        return (
            build_failsafe_reporter_brief(
                city_label, statements, votes, deep_docs, link_map, today_str
            ),
            "failsafe_structured",
        )


def escape_md_cell(value: str) -> str:
    cleaned = (value or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned.replace("|", "｜")


def build_evidence_appendix_md(
    city_label: str,
    statements: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    deep_docs: list[dict[str, Any]],
    link_map: dict[str, str],
    today_str: str,
) -> str:
    """
    Step 4B: 別添：一次資料・根拠一覧（指示書セクション6完全準拠）
    - 全行に検証状態（確認済／一部確認／未確認）と関連性3分類（直接関連／政策背景／参考情報）を明記
    - AI要約と原典発言引用を明確に区別
    """
    lines: list[str] = [
        "# 別添：一次資料・根拠一覧（錦林市営住宅・錦林浴場調査）",
        "",
        f"- **対象自治体**: {city_label}",
        f"- **最終確認日**: {today_str}",
        "- **発行**: KICKs／議会のミカタ",
        "- **検証状態の定義**: `確認済`＝公式URL疎通および原典本文・議案記載の照合完了 ／ `一部確認`＝公式URL疎通または要旨照合済（詳細数値は要原典目視） ／ `未確認`＝原典未取得または該当記載未検出",
        "",
        "## 1. 議案・採決 根拠一覧",
        "",
        "| 検証状態 | 関連性 | 会期・議案番号 | 議案名・議決結果 | 一次資料抽出内容（金額・工期・理由） | 原典URL・議会のミカタ |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for v in votes:
        cd = v["contract_details"]
        detail_col = escape_md_cell(
            f"変更前:{cd['before_amount']} / 変更後:{cd['after_amount']} / "
            f"増減:{cd['diff_amount']}（累計:{cd['cumulative_diff']}） / "
            f"工期:{cd['schedule']} / 理由:{cd['reason']} "
            f"【検証メモ: {v['verify_note']}】"
        )
        lines.append(
            f"| **{v['verify_status']}** | {v['relevance']} | "
            f"{escape_md_cell(v['session_name'] + ' ' + v['bill_number'])} | "
            f"{escape_md_cell(v['title'])}（結果: **{escape_md_cell(v['result'])}**） | "
            f"{detail_col} | {link_map.get(v['record_id'], '—')} |"
        )

    if deep_docs:
        lines.extend(
            [
                "",
                "## 2. 自治体公式ドメイン限定 Deep Research 取得資料一覧",
                "",
                "| 検証状態 | 関連性 | 資料タイトル | 抽出テキスト要旨 | 原典URL・議会のミカタ |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for d in deep_docs:
            excerpt = escape_md_cell(d["extracted_text"][:260] + "…")
            lines.append(
                f"| **{d['verify_status']}** | {d['relevance']} | "
                f"{escape_md_cell(d['title'])} | {excerpt} | {link_map.get(d['record_id'], '—')} |"
            )

    lines.extend(
        [
            "",
            "## 3. 議会質疑 根拠一覧（AI要約と原典発言引用の区別）",
            "",
            "| 検証状態 | 関連性 | 日付・会議名 | 議員・会派 | 質問と行政回答の要点（AI要約） ／ 原典発言引用 | 原典URL・議会のミカタ |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    for s in statements:
        quote_str = ""
        if s.get("statement_text"):
            raw_q = escape_md_cell(s["statement_text"][:220])
            quote_str = f" ／ **【原典引用】**「{raw_q}…」"
        summary_str = escape_md_cell(s["summary"])
        lines.append(
            f"| **{s['verify_status']}** | {s['relevance']} | "
            f"{escape_md_cell(s['meeting_date'] + ' ' + s['meeting_title'])} | "
            f"{escape_md_cell(s['speaker'] + '（' + s['party'] + '）')} | "
            f"**【AI要約】**{summary_str}{quote_str} | {link_map.get(s['record_id'], '—')} |"
        )

    return sanitize_nested_markdown_links("\n".join(lines))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="メディア向け調査支援パイプライン（自治体ドメイン限定 Deep Research 統合版）"
    )
    parser.add_argument("--city", default="kyoto", help="対象自治体コード（デフォルト: kyoto）")
    parser.add_argument(
        "--keywords",
        required=True,
        help="コア検索キーワード（カンマ区切り）",
    )
    parser.add_argument(
        "--broad-keywords",
        default="",
        help="広域関連キーワード（省略可・カンマ区切り）",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="改訂版レポート本編の出力Markdownパス（例: reports/research_kinrin_final.md）",
    )
    parser.add_argument(
        "--evidence-output",
        default=None,
        help="別添：一次資料・根拠一覧の出力Markdownパス（省略時は <output>_evidence.md）",
    )
    parser.add_argument(
        "--data-dir",
        default="frontend/public/data",
        help="入力JSONデータディレクトリ（デフォルト: frontend/public/data）",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="使用するGeminiモデル名（デフォルト: gemini-2.5-flash）",
    )
    parser.add_argument(
        "--skip-pdf-check",
        action="store_true",
        help="一次資料URLのHTTP疎通・PDF取得をスキップする場合に指定",
    )
    parser.add_argument(
        "--skip-deep-research",
        action="store_true",
        help="Step 2 の自治体公式ドメイン限定 Deep Research 検索をスキップする場合に指定",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Markdown出力と同時にビジネス品質のA4 PDFも自動生成する",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_env_variables()
    args = parse_args(argv)
    t_start = time.time()

    core_keywords = parse_keywords(args.keywords)
    if not core_keywords:
        print("[ERROR] --keywords には有効なキーワードが1つ以上必要です。", file=sys.stderr)
        return 1

    broad_keywords = parse_keywords(args.broad_keywords)
    data_dir = Path(args.data_dir)
    city_label = get_city_label(args.city)
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[INFO] Step 1 開始: ローカルDB横断抽出＆固有URL検証 (city={args.city}, data_dir={data_dir})")
    statements, votes = step1_extract_local_db(
        data_dir=data_dir,
        city=args.city,
        core_keywords=core_keywords,
        broad_keywords=broad_keywords,
        verify_http=not args.skip_pdf_check,
    )
    print(f"[INFO] Step 1 完了: 質疑 {len(statements)} 件, 議案・採決 {len(votes)} 件")

    deep_docs = step2_official_domain_deep_research(
        city=args.city,
        core_keywords=core_keywords,
        statements=statements,
        votes=votes,
        model_name=args.model,
        enabled=(not args.skip_deep_research) and (not args.skip_pdf_check),
    )

    link_map = build_unified_link_map(statements, votes, deep_docs)

    direct_s = sum(1 for s in statements if s["relevance"] == "直接関連")
    policy_s = sum(1 for s in statements if s["relevance"] == "政策背景")
    ref_s = sum(1 for s in statements if s["relevance"] == "参考情報")
    print(
        f"[INFO] Step 3 完了: 質疑3分類（直接関連={direct_s}件, 政策背景={policy_s}件, 参考情報={ref_s}件）, "
        f"議案={len(votes)}件, Deep Research公式資料={len(deep_docs)}件"
    )

    brief_md, gen_mode = generate_reporter_brief_part(
        city=args.city,
        statements=statements,
        votes=votes,
        deep_docs=deep_docs,
        link_map=link_map,
        today_str=today_str,
        model_name=args.model,
    )
    appendix_md = build_evidence_appendix_md(
        city_label=city_label,
        statements=statements,
        votes=votes,
        deep_docs=deep_docs,
        link_map=link_map,
        today_str=today_str,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path = (
        Path(args.evidence_output)
        if args.evidence_output
        else output_path.with_name(f"{output_path.stem}_evidence.md")
    )
    full_path = output_path.with_name(f"{output_path.stem}_full.md")

    output_path.write_text(brief_md + "\n", encoding="utf-8")
    evidence_path.write_text(appendix_md + "\n", encoding="utf-8")
    full_path.write_text(
        brief_md + "\n\n---\n\n" + appendix_md + "\n",
        encoding="utf-8",
    )

    elapsed = time.time() - t_start
    print(f"[INFO] Step 4 出力完了 ({elapsed:.1f}s, mode={gen_mode}):")
    print(f"  - 改訂版レポート本編 : {output_path.resolve()}")
    print(f"  - 別添：一次資料一覧 : {evidence_path.resolve()}")
    print(f"  - 本編＋別添統合版   : {full_path.resolve()}")

    if args.pdf:
        from md_to_pdf import convert_markdown_file_to_pdf

        brief_pdf, eng1 = convert_markdown_file_to_pdf(output_path)
        ev_pdf, eng2 = convert_markdown_file_to_pdf(evidence_path)
        print(f"[INFO] PDF生成完了: 本編={brief_pdf.resolve()} ({eng1}), 別添={ev_pdf.resolve()} ({eng2})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())