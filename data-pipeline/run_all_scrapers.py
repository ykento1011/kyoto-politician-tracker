import logging
import sys
import time
from pathlib import Path

CUR = Path(__file__).resolve().parent
if str(CUR) not in sys.path:
    sys.path.insert(0, str(CUR))

from fetch_kyoto_ssp import KyotoKaigirokuScraper
from fetch_osaka_ssp import OsakaKaigirokuScraper
from fetch_yokohama_ssp import YokohamaKaigirokuScraper
from scrapers.kaigiroku_scraper import KaigirokuScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(CUR / "scraper_pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("PipelineRunner")

def main():
    logger.info("==================================================")
    logger.info("🚀 全政令指定都市 議事録データパイプライン 定期差分巡回開始")
    logger.info("==================================================")
    
    start_time = time.time()
    
    # 1. 名古屋市会
    logger.info("--- [1/4] 名古屋市会 差分チェック ---")
    nagoya = KaigirokuScraper(
        city_code="nagoya",
        tenant_id="207",
        tenant_dir="nagoya",
        output_path=CUR / "nagoya_raw_statements.json"
    )
    nagoya.run_fetch()
    
    # 2. 京都市会
    logger.info("--- [2/4] 京都市会 差分チェック ---")
    kyoto = KyotoKaigirokuScraper()
    kyoto.run_fetch()
    
    # 3. 大阪市会
    logger.info("--- [3/4] 大阪市会 差分チェック ---")
    osaka = OsakaKaigirokuScraper()
    osaka.run_fetch()
    
    # 4. 横浜市会
    logger.info("--- [4/4] 横浜市会 差分チェック ---")
    yokohama = YokohamaKaigirokuScraper()
    yokohama.run_fetch()
    
    elapsed = time.time() - start_time
    logger.info("==================================================")
    logger.info(f"🎉 全都市の差分巡回が正常終了しました (所要時間: {elapsed:.1f} 秒)")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
