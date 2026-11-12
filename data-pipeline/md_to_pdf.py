#!/usr/bin/env python3
"""
メディア・法人提出用 Markdown -> ビジネス品質PDF 自動変換スクリプト
- プライマリエンジン: markdown + weasyprint（CSS A4組版・高精細テーブル・クリッカブルURI保持）
- フォールバックエンジン: reportlab（GTK未導入のWindows環境等でもpipのみで100%動作）

Usage:
    python data-pipeline/md_to_pdf.py reports/research_kinrin_final.md
    python data-pipeline/md_to_pdf.py --input reports/research_kinrin_final.md --output reports/research_kinrin_final.pdf
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import Any


# OS別の日本語フォント候補（WeasyPrint / ReportLab 共用）
FONT_CANDIDATES: list[tuple[str, str, int]] = [
    # Linux (Noto Sans CJK / IPAex / Takao)
    ("NotoSansCJKJP", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("NotoSansCJKJP", "/usr/share/fonts/NotoSansCJK-Regular.ttc", 0),
    ("NotoSansJP", "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf", 0),
    ("NotoSansJP", "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.otf", 0),
    ("IPAexGothic", "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf", 0),
    ("IPAexGothic", "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", 0),
    ("TakaoPGothic", "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf", 0),
    # Windows (游ゴシック / メイリオ / BIZ UDゴシック / MS ゴシック)
    ("YuGothic", r"C:\Windows\Fonts\YuGothR.ttc", 0),
    ("YuGothic", r"C:\Windows\Fonts\YuGothM.ttc", 0),
    ("Meiryo", r"C:\Windows\Fonts\meiryo.ttc", 0),
    ("BIZUDGothic", r"C:\Windows\Fonts\BIZ-UDGothicR.ttc", 0),
    ("MSGothic", r"C:\Windows\Fonts\msgothic.ttc", 0),
    # macOS (ヒラギノ角ゴシック / 游ゴシック)
    ("HiraginoSans", "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 0),
    ("HiraginoSans", "/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("YuGothicMac", "/Library/Fonts/YuGothic-Medium.otf", 0),
]

BOLD_FONT_CANDIDATES: list[tuple[str, str, int]] = [
    ("NotoSansCJKJP-Bold", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("NotoSansJP-Bold", "/usr/share/fonts/truetype/noto/NotoSansJP-Bold.ttf", 0),
    ("NotoSansJP-Bold", "/usr/share/fonts/truetype/noto/NotoSansJP-Bold.otf", 0),
    ("YuGothic-Bold", r"C:\Windows\Fonts\YuGothB.ttc", 0),
    ("Meiryo-Bold", r"C:\Windows\Fonts\meiryob.ttc", 0),
    ("BIZUDGothic-Bold", r"C:\Windows\Fonts\BIZ-UDGothicB.ttc", 0),
    ("HiraginoSans-Bold", "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 0),
]


def discover_japanese_font(
    candidates: list[tuple[str, str, int]],
) -> tuple[str, Path, int] | None:
    """実行環境内に存在する日本語フォントファイルを探索して返す。"""
    for family, raw_path, subfont_idx in candidates:
        p = Path(raw_path)
        if p.is_file():
            return family, p, subfont_idx
    return None


def sanitize_markdown_links(md_text: str) -> str:
    """
    二重括弧化したリンク表記 `[label]([https://a/](https://a/)b)` が
    万が一含まれていた場合でも、標準の `[label](https://a/b)` へ正規化する。
    """
    return re.sub(
        r"\]\(\[(https?://[^\]]+)\]\(\1\)([^\)]*)\)",
        r"](\1\2)",
        md_text,
    )


def build_weasyprint_css(
    regular_font: tuple[str, Path, int] | None,
    bold_font: tuple[str, Path, int] | None,
) -> str:
    """記者・法人提出用のA4ビジネスレポートCSSを生成する。"""
    font_face_blocks: list[str] = []
    primary_family = "ReportJPFont"

    if regular_font:
        _, reg_path, _ = regular_font
        font_face_blocks.append(
            f"""
@font-face {{
    font-family: "{primary_family}";
    src: url("{reg_path.as_uri()}");
    font-weight: 400;
    font-style: normal;
}}"""
        )
    if bold_font:
        _, bold_path, _ = bold_font
        font_face_blocks.append(
            f"""
@font-face {{
    font-family: "{primary_family}";
    src: url("{bold_path.as_uri()}");
    font-weight: 700;
    font-style: normal;
}}"""
        )

    font_faces_css = "\n".join(font_face_blocks)

    return f"""
{font_faces_css}

@page {{
    size: A4 portrait;
    margin: 16mm 12mm 17mm 12mm;
    @top-right {{
        content: "議会調査レポート（検証用一次資料リンク付）";
        font-family: "{primary_family}", "Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "Yu Gothic", "Meiryo", sans-serif;
        font-size: 7.5pt;
        color: #64748b;
    }}
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-family: "{primary_family}", "Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "Yu Gothic", "Meiryo", sans-serif;
        font-size: 8pt;
        color: #475569;
    }}
}}

* {{
    box-sizing: border-box;
}}

body {{
    font-family: "{primary_family}", "Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "Yu Gothic", "Meiryo", "Hiragino Kaku Gothic ProN", sans-serif;
    font-size: 9.5pt;
    line-height: 1.62;
    color: #1e293b;
    margin: 0;
    padding: 0;
    overflow-wrap: break-word;
    word-wrap: break-word;
}}

/* H1: レポートメインタイトル */
h1 {{
    font-size: 16pt;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.35;
    margin: 0 0 10pt 0;
    padding: 8pt 10pt;
    background-color: #f1f5f9;
    border-left: 4.5pt solid #1e3a5f;
    border-bottom: 1.8pt solid #1e3a5f;
}}

/* H2: 第1部・第2部セクション見出し */
h2 {{
    font-size: 12.5pt;
    font-weight: 700;
    color: #1e3a5f;
    line-height: 1.35;
    margin: 16pt 0 8pt 0;
    padding-bottom: 3.5pt;
    border-bottom: 1.4pt solid #1e3a5f;
    page-break-after: avoid;
    break-after: avoid;
}}

/* H3: サブセクション見出し（1. 調査概要〜4. 今後の確認事項） */
h3 {{
    font-size: 10.5pt;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.35;
    margin: 12pt 0 5pt 0;
    padding: 2.5pt 0 2.5pt 7pt;
    border-left: 3pt solid #2563eb;
    border-bottom: 0.6pt solid #cbd5e1;
    page-break-after: avoid;
    break-after: avoid;
}}

p {{
    margin: 0 0 6pt 0;
    text-align: justify;
}}

ul, ol {{
    margin: 3pt 0 8pt 0;
    padding-left: 16pt;
}}

li {{
    margin-bottom: 4.5pt;
    line-height: 1.58;
}}

li > ul, li > ol {{
    margin-top: 2.5pt;
    margin-bottom: 3pt;
}}

hr {{
    border: none;
    border-top: 0.8pt solid #cbd5e1;
    margin: 10pt 0;
}}

code {{
    font-family: "{primary_family}", "Noto Sans CJK JP", "Yu Gothic", monospace;
    font-size: 8.5pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1pt 3.5pt;
    border-radius: 2pt;
    border: 0.4pt solid #e2e8f0;
}}

/* クリッカブルハイパーリンク（視認性の高い青色＋下線） */
a {{
    color: #1d4ed8;
    text-decoration: underline;
    font-weight: 500;
}}

/* 第2部：根拠一覧テーブル（A4幅に完全フィット・長文自動折り返し） */
table {{
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    margin: 6pt 0 10pt 0;
    font-size: 7.6pt;
    line-height: 1.42;
}}

thead {{
    display: table-header-group;
}}

tr {{
    page-break-inside: avoid;
    break-inside: avoid;
}}

th {{
    background-color: #1e3a5f;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 5pt 4pt;
    border: 0.6pt solid #1e3a5f;
    vertical-align: middle;
}}

td {{
    padding: 4.5pt 4pt;
    border: 0.5pt solid #cbd5e1;
    vertical-align: top;
    color: #1e293b;
    overflow-wrap: anywhere;
    word-wrap: break-word;
    word-break: break-word;
}}

tbody tr:nth-child(even) td {{
    background-color: #f8fafc;
}}

/* 6列テーブル（日付・会期 | 区分 | 議員・会派 | 要旨・採決結果 | 一次資料 | 議会のミカタ）の列幅比率 */
table.evidence-table col.col-date {{ width: 15%; }}
table.evidence-table col.col-type {{ width: 10.5%; }}
table.evidence-table col.col-speaker {{ width: 18.5%; }}
table.evidence-table col.col-summary {{ width: 34%; }}
table.evidence-table col.col-primary {{ width: 11%; }}
table.evidence-table col.col-mikata {{ width: 11%; }}
"""


def inject_table_colgroup(html_body: str) -> str:
    """
    6列の根拠一覧テーブルに <colgroup> と class="evidence-table" を付与し、
    長文カラム（要旨・採決結果）とURLカラムがA4幅からはみ出さないように制御する。
    """
    colgroup_html = (
        '<table class="evidence-table">'
        "<colgroup>"
        '<col class="col-date" />'
        '<col class="col-type" />'
        '<col class="col-speaker" />'
        '<col class="col-summary" />'
        '<col class="col-primary" />'
        '<col class="col-mikata" />'
        "</colgroup>"
    )
    return html_body.replace("<table>", colgroup_html)


def convert_with_weasyprint(md_text: str, output_pdf: Path) -> None:
    """markdown + weasyprint を用いてHTML/CSS経由で高品質A4 PDFを生成する。"""
    import markdown  # type: ignore
    import weasyprint  # type: ignore

    cleaned_md = sanitize_markdown_links(md_text)
    html_fragment = markdown.markdown(
        cleaned_md,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )
    html_fragment = inject_table_colgroup(html_fragment)

    regular_font = discover_japanese_font(FONT_CANDIDATES)
    bold_font = discover_japanese_font(BOLD_FONT_CANDIDATES)
    css_text = build_weasyprint_css(regular_font, bold_font)

    full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>議会調査レポート</title>
</head>
<body>
{html_fragment}
</body>
</html>
"""
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    weasyprint.HTML(string=full_html, base_url=str(output_pdf.parent.resolve())).write_pdf(
        target=str(output_pdf),
        stylesheets=[weasyprint.CSS(string=css_text)],
    )


def inline_md_to_reportlab_xml(text: str, font_bold: str) -> str:
    """
    ReportLab Paragraph用のインラインマークアップ（太字・インラインコード・青色クリッカブルリンク）変換。
    """
    tokens: list[str] = []

    def _stash(xml_fragment: str) -> str:
        idx = len(tokens)
        tokens.append(xml_fragment)
        return f"@@TOK{idx}@@"

    # 1. Markdownリンク [label](url) -> 青色下線リンク
    def _link_repl(m: re.Match[str]) -> str:
        label = html.escape(m.group(1))
        url = html.escape(m.group(2), quote=True)
        return _stash(f'<a href="{url}" color="#1d4ed8"><u>{label}</u></a>')

    working = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", _link_repl, text)

    # 2. インラインコード `code`
    def _code_repl(m: re.Match[str]) -> str:
        code_txt = html.escape(m.group(1))
        return _stash(f'<font backColor="#f1f5f9" color="#0f172a"> {code_txt} </font>')

    working = re.sub(r"`([^`]+)`", _code_repl, working)

    # 3. 太字 **bold**
    def _bold_repl(m: re.Match[str]) -> str:
        bold_txt = html.escape(m.group(1))
        return _stash(f'<font name="{font_bold}"><b>{bold_txt}</b></font>')

    working = re.sub(r"\*\*([^*]+)\*\*", _bold_repl, working)

    escaped = html.escape(working)
    for idx, frag in enumerate(tokens):
        escaped = escaped.replace(f"@@TOK{idx}@@", frag)
    return escaped


def register_reportlab_japanese_fonts() -> tuple[str, str]:
    """
    ReportLab用にTrueTypeアウトラインを持つ日本語フォントを登録する。
    CFF/PostScriptアウトラインのみのフォントしか無い場合は組み込みCIDフォントへフォールバックする。
    """
    from reportlab.pdfbase import pdfmetrics  # type: ignore
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore
    from reportlab.pdfbase.ttfonts import TTFont  # type: ignore

    reg_name: str | None = None
    bold_name: str | None = None

    for family, raw_path, subfont_idx in FONT_CANDIDATES:
        p = Path(raw_path)
        if not p.is_file():
            continue
        try:
            pdfmetrics.registerFont(TTFont(family, str(p), subfontIndex=subfont_idx))
            reg_name = family
            break
        except Exception:
            continue

    if reg_name:
        for family, raw_path, subfont_idx in BOLD_FONT_CANDIDATES:
            p = Path(raw_path)
            if not p.is_file():
                continue
            try:
                pdfmetrics.registerFont(TTFont(family, str(p), subfontIndex=subfont_idx))
                bold_name = family
                break
            except Exception:
                continue
        if not bold_name:
            bold_name = reg_name
        pdfmetrics.registerFontFamily(
            reg_name,
            normal=reg_name,
            bold=bold_name,
            italic=reg_name,
            boldItalic=bold_name,
        )
        return reg_name, bold_name

    # Fallback: ReportLab標準日本語CIDフォント（フォントファイル不要で確実に日本語・英数字を描画可能）
    cid_name = "HeiseiKakuGo-W5"
    pdfmetrics.registerFont(UnicodeCIDFont(cid_name))
    return cid_name, cid_name


def convert_with_reportlab(md_text: str, output_pdf: Path) -> None:
    """
    ReportLab を用いたフォールバックPDF生成エンジン（GTKランタイム不要・Windowsでもpipのみで動作）。
    日本語フォント登録・H1〜H3ボーダー・青色クリッカブルリンク・A4幅自動折り返しテーブルを再現する。
    """
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import ParagraphStyle  # type: ignore
    from reportlab.lib.units import mm  # type: ignore
    from reportlab.platypus import (  # type: ignore
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    reg_name, bold_name = register_reportlab_japanese_fonts()

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="議会調査レポート",
    )

    style_h1 = ParagraphStyle(
        "H1",
        fontName=bold_name,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=(6, 8, 6, 8),
        spaceAfter=8,
    )
    style_h2 = ParagraphStyle(
        "H2",
        fontName=bold_name,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=12,
        spaceAfter=4,
    )
    style_h3 = ParagraphStyle(
        "H3",
        fontName=bold_name,
        fontSize=10.5,
        leading=14.5,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=9,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "Body",
        fontName=reg_name,
        fontSize=9.2,
        leading=14.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )
    style_bullet = ParagraphStyle(
        "Bullet",
        fontName=reg_name,
        fontSize=9.0,
        leading=14.0,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3.5,
    )
    style_sub_bullet = ParagraphStyle(
        "SubBullet",
        fontName=reg_name,
        fontSize=8.8,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=24,
        firstLineIndent=-8,
        spaceAfter=3,
    )
    style_th = ParagraphStyle(
        "TH",
        fontName=bold_name,
        fontSize=7.6,
        leading=10.5,
        textColor=colors.white,
    )
    style_td = ParagraphStyle(
        "TD",
        fontName=reg_name,
        fontSize=7.4,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
        wordWrap="CJK",
    )

    cleaned_md = sanitize_markdown_links(md_text)
    lines = cleaned_md.splitlines()
    story: list[Any] = []
    table_buffer: list[list[str]] = []

    def _flush_table() -> None:
        nonlocal table_buffer
        if not table_buffer:
            return
        data_rows = [
            r
            for r in table_buffer
            if not all(re.fullmatch(r":?-+:?", cell.strip()) for cell in r)
        ]
        table_buffer = []
        if not data_rows:
            return

        avail_w = A4[0] - (24 * mm)
        num_cols = len(data_rows[0])
        if num_cols == 6:
            col_widths = [
                avail_w * 0.15,
                avail_w * 0.105,
                avail_w * 0.185,
                avail_w * 0.34,
                avail_w * 0.11,
                avail_w * 0.11,
            ]
        else:
            col_widths = [avail_w / max(num_cols, 1)] * num_cols

        formatted_rows: list[list[Paragraph]] = []
        for r_idx, row in enumerate(data_rows):
            cell_style = style_th if r_idx == 0 else style_td
            formatted_rows.append(
                [
                    Paragraph(inline_md_to_reportlab_xml(c.strip(), bold_name), cell_style)
                    for c in row
                ]
            )

        tbl = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Spacer(1, 3 * mm))
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_buffer.append(cells)
            continue
        else:
            _flush_table()

        if not stripped:
            continue

        if stripped == "---":
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=colors.HexColor("#cbd5e1"),
                    spaceBefore=4,
                    spaceAfter=6,
                )
            )
            continue

        if stripped.startswith("# "):
            story.append(
                Paragraph(inline_md_to_reportlab_xml(stripped[2:], bold_name), style_h1)
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=1.6,
                    color=colors.HexColor("#1e3a5f"),
                    spaceBefore=0,
                    spaceAfter=6,
                )
            )
            continue

        if stripped.startswith("## "):
            story.append(
                Paragraph(inline_md_to_reportlab_xml(stripped[3:], bold_name), style_h2)
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=1.2,
                    color=colors.HexColor("#1e3a5f"),
                    spaceBefore=0,
                    spaceAfter=5,
                )
            )
            continue

        if stripped.startswith("### "):
            story.append(
                Paragraph(inline_md_to_reportlab_xml(stripped[4:], bold_name), style_h3)
            )
            continue

        m_sub = re.match(r"^\s{2,}(?:[-*]|\d+\.)\s+(.*)$", raw_line)
        if m_sub:
            content = inline_md_to_reportlab_xml(m_sub.group(1), bold_name)
            story.append(Paragraph(f"▪ {content}", style_sub_bullet))
            continue

        m_bullet = re.match(r"^(?:[-*]|(\d+)\.)\s+(.*)$", stripped)
        if m_bullet:
            num_prefix = f"{m_bullet.group(1)}. " if m_bullet.group(1) else "• "
            content = inline_md_to_reportlab_xml(m_bullet.group(2), bold_name)
            story.append(Paragraph(f"{num_prefix}{content}", style_bullet))
            continue

        story.append(
            Paragraph(inline_md_to_reportlab_xml(stripped, bold_name), style_body)
        )

    _flush_table()

    def _draw_footer(canvas_obj: Any, doc_obj: Any) -> None:
        canvas_obj.saveState()
        canvas_obj.setFont(reg_name, 8)
        canvas_obj.setFillColor(colors.HexColor("#475569"))
        canvas_obj.drawCentredString(
            A4[0] / 2.0, 9 * mm, f"Page {doc_obj.page}"
        )
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)


def convert_markdown_file_to_pdf(
    input_md: Path,
    output_pdf: Path | None = None,
    engine: str = "auto",
) -> tuple[Path, str]:
    """
    Markdownファイルをビジネス品質PDFへ変換するメインエントリポイント。
    Returns: (出力PDFパス, 使用エンジン名)
    """
    if not input_md.is_file():
        raise FileNotFoundError(f"入力Markdownファイルが見つかりません: {input_md}")

    target_pdf = output_pdf if output_pdf is not None else input_md.with_suffix(".pdf")
    md_text = input_md.read_text(encoding="utf-8")

    if engine == "weasyprint":
        convert_with_weasyprint(md_text, target_pdf)
        return target_pdf, "weasyprint"

    if engine == "reportlab":
        convert_with_reportlab(md_text, target_pdf)
        return target_pdf, "reportlab"

    # auto: markdown + weasyprint を優先し、GTK未導入等の環境では reportlab へ自動フォールバック
    try:
        convert_with_weasyprint(md_text, target_pdf)
        return target_pdf, "weasyprint"
    except Exception as exc:
        print(
            f"[WARN] weasyprint でのPDF生成をスキップし、reportlab エンジンへフォールバックします ({exc})",
            file=sys.stderr,
        )
        convert_with_reportlab(md_text, target_pdf)
        return target_pdf, "reportlab (fallback)"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="議会調査Markdownレポートをビジネス提出品質のA4 PDFへ自動変換する"
    )
    parser.add_argument(
        "positional_input",
        nargs="?",
        help="入力Markdownファイルパス（例: reports/research_kinrin_final.md）",
    )
    parser.add_argument(
        "--input",
        dest="opt_input",
        help="入力Markdownファイルパス（位置引数でも指定可）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="出力PDFファイルパス（省略時は入力と同階層・拡張子 .pdf で出力）",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "weasyprint", "reportlab"],
        default="auto",
        help="PDF変換エンジン（デフォルト: auto = weasyprint優先・未対応環境ではreportlab自動切替）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw_input = args.opt_input or args.positional_input
    if not raw_input:
        print(
            "[ERROR] 入力Markdownファイルパスを指定してください（例: python data-pipeline/md_to_pdf.py reports/research_kinrin_final.md）",
            file=sys.stderr,
        )
        return 1

    input_path = Path(raw_input)
    output_path = Path(args.output) if args.output else None

    print(f"[INFO] PDF変換開始: input={input_path}, engine={args.engine}")
    resolved_pdf, used_engine = convert_markdown_file_to_pdf(
        input_md=input_path,
        output_pdf=output_path,
        engine=args.engine,
    )
    print(f"[INFO] PDF変換完了: engine={used_engine}, output={resolved_pdf.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())