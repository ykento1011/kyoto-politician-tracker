import argparse
import logging
import sys
from pathlib import Path

CUR = Path(__file__).resolve().parent
if str(CUR) not in sys.path:
    sys.path.insert(0, str(CUR))

from scrapers.kaigiroku_scraper import KaigirokuScraper

OUTPUT_RAW = CUR / "osaka_raw_statements.json"

class OsakaKaigirokuScraper(KaigirokuScraper):
    def __init__(self, output_path: Path = OUTPUT_RAW, rate_limit_seconds: float = 1.2):
        super().__init__(
            city_code="osaka",
            tenant_id="357",
            tenant_dir="cityosaka",
            output_path=output_path,
            rate_limit_seconds=rate_limit_seconds,
        )

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="大阪市会 SSP 会議録フェッチャー")
    parser.add_argument("--start-date", type=str, default="2023-05-01", help="現任期開始日 (YYYY-MM-DD)")
    parser.add_argument("--rate-limit", type=float, default=1.2, help="リクエスト間隔（秒）")
    parser.add_argument("--max-councils", type=int, default=None, help="取得上限会議数")
    args = parser.parse_args()

    scraper = OsakaKaigirokuScraper(rate_limit_seconds=args.rate_limit)
    scraper.run_fetch(start_date=args.start_date, max_councils=args.max_councils)

if __name__ == "__main__":
    main()
