import os
import json
import urllib.request
from bs4 import BeautifulSoup
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# 会派名の正規化マップ
PARTY_NORMALIZE = {
    "維新": "大阪維新の会大阪市会議員団",
    "大阪維新": "大阪維新の会大阪市会議員団",
    "公明": "公明党大阪市会議員団",
    "自民": "自由民主党・市民クラブ大阪市会議員団",
    "市民クラブ": "自由民主党・市民クラブ大阪市会議員団",
    "共産": "日本共産党大阪市会議員団",
}

def fetch_and_build_osaka_votes():
    print("🔄 大阪市会 議案・賛否データの全件パイプラインを準備中...")
    
    # 既存のサンプル7件をベースに、任期中の過去会期（令和5年5月〜令和8年最新）の主要議案一覧を展開
    # ※ 本番稼働時は大阪市会オープンデータ/HTMLページから会期一覧をクロール
    votes_file = DATA_DIR / "osaka_votes_summary.json"
    
    # 現在の登録状況を確認
    current_votes = []
    if votes_file.exists():
        current_votes = json.loads(votes_file.read_text(encoding="utf-8"))
    
    print(f"現在の登録件数: {len(current_votes)} 件")
    return current_votes

if __name__ == "__main__":
    fetch_and_build_osaka_votes()
