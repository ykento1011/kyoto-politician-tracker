"""
fetch_kobe_discuss.py
神戸市会 会議録検索システム（DiscussNet Premium）フェッチャー
共通基盤 DiscussScraper を継承して配備
"""
import argparse
import logging
import sys
from pathlib import Path

CUR = Path(__file__).resolve().parent
if str(CUR) not in sys.path:
    sys.path.insert(0, str(CUR))

from scrapers.discuss_scraper import DiscussScraper

BASE_URL = "https://www.city.kobe.hyogo.dbsr.jp"
OUTPUT_RAW = CUR / "kobe_raw_statements.json"

class KobeDiscussScraper(DiscussScraper):
    """神戸市会向け DiscussNet スクレイパー"""
    def __init__(self, output_path: Path = OUTPUT_RAW, rate_limit_seconds: float = 1.2):
        super().__init__(
            city_code="kobe",
            base_url=BASE_URL,
            output_path=output_path,
            rate_limit_seconds=rate_limit_seconds,
        )

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="神戸市会 DiscussNet 全任期フェッチャー")
    parser.add_argument("--start-date", type=str, default="2023-05-01", help="現任期開始日 (YYYY-MM-DD)")
    parser.add_argument("--rate-limit", type=float, default=1.2, help="リクエスト間隔（秒、最低1.0秒）")
    args = parser.parse_args()

    scraper = KobeDiscussScraper(rate_limit_seconds=args.rate_limit)
    scraper.run_fetch(start_date=args.start_date)

if __name__ == "__main__":
    main()
