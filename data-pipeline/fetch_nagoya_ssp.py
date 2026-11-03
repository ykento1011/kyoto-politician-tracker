"""
fetch_nagoya_ssp.py
名古屋市会 会議録検索システム（SideStaff / 会議録ネット）フェッチャー
共通基盤 KaigirokuScraper を継承して配備
"""
import argparse
import logging
import sys
from pathlib import Path

CUR = Path(__file__).resolve().parent
if str(CUR) not in sys.path:
    sys.path.insert(0, str(CUR))

from scrapers.kaigiroku_scraper import KaigirokuScraper

OUTPUT_RAW = CUR / "nagoya_raw_statements.json"

class NagoyaKaigirokuScraper(KaigirokuScraper):
    """名古屋市会向け KaigirokuScraper (tenant_id=207)"""
    def __init__(self, output_path: Path = OUTPUT_RAW, rate_limit_seconds: float = 1.2):
        super().__init__(
            city_code="nagoya",
            tenant_id="207",
            tenant_dir="nagoya",
            output_path=output_path,
            rate_limit_seconds=rate_limit_seconds,
        )

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="名古屋市会 SSP 会議録フェッチャー")
    parser.add_argument("--start-date", type=str, default="2023-05-01", help="現任期開始日 (YYYY-MM-DD)")
    parser.add_argument("--rate-limit", type=float, default=1.2, help="リクエスト間隔（秒、最低1.0秒）")
    parser.add_argument("--max-councils", type=int, default=None, help="取得する会議数の上限（テスト検証用）")
    args = parser.parse_args()

    scraper = NagoyaKaigirokuScraper(rate_limit_seconds=args.rate_limit)
    scraper.run_fetch(start_date=args.start_date, max_councils=args.max_councils)

if __name__ == "__main__":
    main()
