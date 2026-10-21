import os
import sys
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_JSON = BASE_DIR.parent / "frontend" / "public" / "data" / "mayor_tracker.json"

# 💡 京都市公式確定版公文書URLへ差し替え
MAYOR_INFO = {
    "name": "松井孝治",
    "term_number": 27,
    "term_start": "2024-02-25",
    "election_date": "2024-02-04",
    "bulletin_pdf": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf",
    "strategy_main_pdf": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/sinkyotosenryaku.pdf",
    "strategy_policy_pdf": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
}

# 💡 看板公約14項目 × 新京都戦略（確定版）× 予算主要事業 定量マッピング
PLEDGES_MASTER = [
    {
        "id": "P-01",
        "category": "観光・交通 / 市民生活",
        "headline": "市バス等の「市民優先価格（2階建て運賃）」導入への挑戦",
        "stage_level": 3,
        "stage_label": "予算化・実証中",
        "election_promise": {
            "quote": "国との連携による全国初のパイロットプロジェクトとなる市バス等の『市民優先価格』への挑戦など、市民が観光の意義や効果を実感できる環境づくり",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "重点プロジェクト「市民生活と調和した持続可能な観光と移動」に明記。国とのパイロットプロジェクトを通じた市民優先の運賃体系導入方針を市の総合戦略として公式確定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "市民優先価格導入に向けた広報周知及びバスシステム改修支援事業",
                "department": "交通局自動車部 / 建設局",
                "amount_jpy": 271000000,
                "amount_display": "2億7,100万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税充当", "amount": "2億7,100万円 (100%)", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"}
                ],
                "doc_source": "令和8年度予算案記者会見資料 p.15",
                "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000349/349867/kaikenshiryo.pdf"
            },
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "旅客流動調査・データ分析基盤整備事業（観光特急バス等検証）",
                "department": "交通局自動車部",
                "amount_jpy": 269000000,
                "amount_display": "2億6,900万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税", "amount": "1億8,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "8,900万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案記者会見資料 p.15",
                "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000349/349867/kaikenshiryo.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和7年9月市会",
            "bill_number": "議88",
            "bill_title": "京都市自動車運送事業条例の一部を改正する条例の制定について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "賛成"
            }
        },
        "milestone": {
            "date": "2024-06-01",
            "title": "観光特急バス（EX100・EX101系統）運行開始",
            "status": "achieved"
        }
    },
    {
        "id": "P-02",
        "category": "財政・税制",
        "headline": "宿泊税上限引き上げおよび使途の拡大",
        "stage_level": 4,
        "stage_label": "条例改正案可決・国協議中",
        "election_promise": {
            "quote": "宿泊税の引き上げや使途の拡大により、市民生活と調和した持続可能な観光振興財源を確保します。",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「持続可能な行財政運営の確立」の基幹戦略として明記。観光課題解決・インフラ受入環境整備への使途拡充および最高税額見直しを公式計画化。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "宿泊税制度見直し検討及び観光客受入環境充実支援事業",
                "department": "行財政局税務部 / 観光政策室",
                "amount_jpy": 110000000,
                "amount_display": "1億1,000万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税充当", "amount": "1億1,000万円 (100%)", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"}
                ],
                "doc_source": "令和8年度主要事業説明書（観光政策室分）",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000348/348991/R8_jigyo_kanko.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和7年11月市会",
            "bill_number": "議145",
            "bill_title": "京都市宿泊税条例の一部を改正する条例の制定について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "反対"
            }
        },
        "milestone": {
            "date": "2025-12-15",
            "title": "市会本会議にて宿泊税条例改正案が賛成多数で可決",
            "status": "achieved"
        }
    },
    {
        "id": "P-03",
        "category": "子育て・教育",
        "headline": "全員制中学校給食の早期完全実施（京都方式）",
        "stage_level": 4,
        "stage_label": "給食センター契約可決・着工",
        "election_promise": {
            "quote": "全員制中学校給食の早期実現。食育と温かい給食をすべての中学生に届けます。",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「子育て環境日本一・健やかな学びの保障」に明記。PFI給食センター整備と親子方式の連携による全市立中学校での完全実施工程を法定計画として位置づけ。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "中学校給食完全実施推進事業（給食センターPFI・配膳室改修）",
                "department": "教育委員会体育健康教育室",
                "amount_jpy": 124000000,
                "amount_display": "1億2,400万円",
                "funding_sources": [
                    {"type": "specific", "label": "国費", "amount": "4,000万円", "color": "bg-blue-50 text-blue-700 border-blue-200"},
                    {"type": "debt", "label": "市債", "amount": "7,000万円", "color": "bg-amber-50 text-amber-700 border-amber-200"},
                    {"type": "general", "label": "一般財源", "amount": "1,400万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（教育委員会分） p.8",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000336/336421/R7_jigyo_kyoiku.pdf"
            },
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "市立学校給食費負担軽減・食材費高騰分公費負担事業",
                "department": "教育委員会体育健康教育室",
                "amount_jpy": 190000000,
                "amount_display": "1億9,000万円",
                "funding_sources": [
                    {"type": "general", "label": "一般財源", "amount": "1億9,000万円 (100%)", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案主要事業説明書 p.12",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000348/348991/R8_jigyo_kyoiku.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和7年9月市会",
            "bill_number": "議104",
            "bill_title": "京都市学校給食センター(仮称)整備運営事業実施契約の締結について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "反対"
            }
        },
        "milestone": {
            "date": "2025-10-24",
            "title": "給食センター事業実施契約議案が市会で可決・着工",
            "status": "achieved"
        }
    },
    {
        "id": "P-04",
        "category": "子育て・福祉",
        "headline": "府市協調子ども医療費助成拡充と第2子以降保育料無償化",
        "stage_level": 4,
        "stage_label": "条例可決・制度施行",
        "election_promise": {
            "quote": "京都府との強固な連携により、子どもの医療費助成を拡充し、第2子以降の保育料無償化を進めます。",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「府市協調・子育て負担軽減プロジェクト」に位置づけ。小児通院医療費の自己負担上限月200円の対象拡充および多子世帯の保育料無償化推進を公式確定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "子ども医療費支給事業（通院助成対象年齢拡充・府制度連携）",
                "department": "子ども若者はぐくみ局幼保支援課",
                "amount_jpy": 1420000000,
                "amount_display": "14億2,000万円",
                "funding_sources": [
                    {"type": "specific", "label": "府補助金", "amount": "4億8,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "9億4,000万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（はぐくみ局分） p.14",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000336/336421/R7_jigyo_hagukumi.pdf"
            },
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "多子世帯保育料軽減拡充事業（第2子以降無償化）",
                "department": "子ども若者はぐくみ局幼保支援課",
                "amount_jpy": 1400000000,
                "amount_display": "14億円",
                "funding_sources": [
                    {"type": "specific", "label": "府補助金", "amount": "4億5,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "9億5,000万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（はぐくみ局分） p.16",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000336/336421/R7_jigyo_hagukumi.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和6年11月市会",
            "bill_number": "議162",
            "bill_title": "京都市子ども医療費支給条例等の一部を改正する条例の制定について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "賛成"
            }
        },
        "milestone": {
            "date": "2024-09-01",
            "title": "通院医療費月200円上限の対象を小学校卒業まで完全拡充",
            "status": "achieved"
        }
    },
    {
        "id": "P-05",
        "category": "景観・居住",
        "headline": "京町家保全継承・若年子育て世帯居住支援",
        "stage_level": 3,
        "stage_label": "予算化・改修支援中",
        "election_promise": {
            "quote": "失われゆく京町家を守るため、固定資産税・相続税負担の軽減と、リノベーション・活用の規制緩和を断行します。",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「歴史都市京都の景観・町家継承と若者定住」に明記。居住用町家の改修助成拡充や税負担軽減措置の制度設計を法定計画に位置づけ。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "京町家保全・継承事業（改修補助・景観まちづくりセンター機能強化）",
                "department": "都市計画局まち再生・景観政策部",
                "amount_jpy": 462000000,
                "amount_display": "4億6,200万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税", "amount": "3億2,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "1億4,200万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案主要事業説明書（都市計画局）",
                "doc_url": "https://www.city.kyoto.lg.jp/tokei/cmsfiles/contents/0000348/348991/R8_tokei_machiya.pdf"
            },
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "若年・子育て世帯既存住宅購入・リフォーム支援（京都安心すまい応援金）",
                "department": "都市計画局住宅政策部",
                "amount_jpy": 280000000,
                "amount_display": "2億8,000万円",
                "funding_sources": [
                    {"type": "specific", "label": "国費", "amount": "9,000万円", "color": "bg-blue-50 text-blue-700 border-blue-200"},
                    {"type": "general", "label": "一般財源", "amount": "1億9,000万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（都市計画局） p.22",
                "doc_url": "https://www.city.kyoto.lg.jp/tokei/cmsfiles/contents/0000336/336421/R7_tokei_sumai.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-10-01",
            "title": "京町家カルテ制度のデジタル化・流通プラットフォーム運用開始",
            "status": "achieved"
        }
    },
    {
        "id": "P-06",
        "category": "都市計画",
        "headline": "京都駅周辺・三条京阪都市再生・ビジネス集積",
        "stage_level": 3,
        "stage_label": "計画策定・推進中",
        "election_promise": {
            "quote": "京都駅南部や三条京阪をはじめ、高さ・容積率規制の戦略的見直しによるオフィス・研究開発拠点の集積",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「都市再生・産業立地戦略」の最重点ゾーンとして指定。京都駅東南部および三条京阪における高機能オフィス誘導と都市計画特例活用を確定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "文化芸術シンボルゾーン創出・市有地活用推進事業",
                "department": "総合企画局プロジェクト推進室",
                "amount_jpy": 52000000,
                "amount_display": "5,200万円",
                "funding_sources": [
                    {"type": "general", "label": "一般財源", "amount": "5,200万円 (100%)", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（総合企画局） p.5",
                "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000336/336421/R7_sogo_project.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和7年2月市会",
            "bill_number": "議32",
            "bill_title": "京都市都市計画関係手数料条例の一部を改正する条例の制定について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "反対"
            }
        },
        "milestone": {
            "date": "2024-12-01",
            "title": "京都駅東南部エリアのまちづくり方針改定案公表",
            "status": "achieved"
        }
    },
    {
        "id": "P-07",
        "category": "産業振興",
        "headline": "スタートアップ創出・京都シリコンバレー化構想",
        "stage_level": 3,
        "stage_label": "予算執行・拠点形成中",
        "election_promise": {
            "quote": "大学の知と伝統の融合によるスタートアップ・エコシステムの確立と、世界から挑戦者が集まるインキュベーション機能の強化",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「知恵産業創造・グローバルスタートアップ拠点化」プログラムに明記。大学発ディープテック実証拠点の整備と国内外ベンチャーキャピタル呼び込みを策定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "スタートアップ支援及び企業立地促進強化事業",
                "department": "産業観光局スタートアップ推進室",
                "amount_jpy": 715000000,
                "amount_display": "7億1,500万円",
                "funding_sources": [
                    {"type": "specific", "label": "国費", "amount": "2億1,000万円", "color": "bg-blue-50 text-blue-700 border-blue-200"},
                    {"type": "specific", "label": "宿泊税", "amount": "1億5,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "3億5,500万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案主要事業説明書（産業観光局）",
                "doc_url": "https://www.city.kyoto.lg.jp/sankan/cmsfiles/contents/0000348/348991/R8_sankan_startup.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-07-04",
            "title": "国内最大級スタートアップカンファレンス「IVS京都」開催支援",
            "status": "achieved"
        }
    },
    {
        "id": "P-08",
        "category": "行政改革",
        "headline": "しごとの仕方改革・行政DX・BPR推進",
        "stage_level": 3,
        "stage_label": "庁内改革実行中",
        "election_promise": {
            "quote": "縦割り行政の打破、庁内ペーパーレスの徹底、現場職員の提案が政策化されるクリエイティブな市役所への脱皮",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「クリエイティブ市役所変革・DX推進」に位置づけ。ガバメントクラウド標準化対応、行政手続オンライン化率95%目標、BPR徹底を公式計画化。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "職場のデジタル環境整備及び業務プロセス改革（BPR）推進事業",
                "department": "総合企画局デジタル化推進室",
                "amount_jpy": 160000000,
                "amount_display": "1億6,000万円",
                "funding_sources": [
                    {"type": "general", "label": "一般財源", "amount": "1億6,000万円 (100%)", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（総合企画局デジタル化推進室）",
                "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000336/336421/R7_sogo_digital.pdf"
            },
            {
                "fiscal_year": "令和7年度 9月補正",
                "project_name": "自治体情報システム標準化対応事業",
                "department": "総合企画局デジタル化推進室",
                "amount_jpy": 420000000,
                "amount_display": "4億2,000万円",
                "funding_sources": [
                    {"type": "specific", "label": "国庫補助金", "amount": "4億2,000万円 (100%)", "color": "bg-blue-50 text-blue-700 border-blue-200"}
                ],
                "doc_source": "令和7年度9月補正予算概要 p.3",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000341/341201/R7_09hosei_gaiyo.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-04-01",
            "title": "市長直轄「政策企画・改革推進室」の新設",
            "status": "achieved"
        }
    },
    {
        "id": "P-09",
        "category": "財政規律",
        "headline": "持続可能な行財政運営・過去負債返済の堅持",
        "stage_level": 3,
        "stage_label": "黒字決算堅持・負債返済中",
        "election_promise": {
            "quote": "将来世代に借金のツケを回さない。行財政改革の成果を維持し、実質収支黒字を堅持します。",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「財政規律と公債償還の堅持」を戦略全体の最重要前提条件として位置づけ。公債償還基金取崩し分の計画的返済完了に向けたロードマップを策定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 9月補正",
                "project_name": "過去負債返済（公債償還基金計画外取崩しの償還）",
                "department": "行財政局財政部",
                "amount_jpy": 2500000000,
                "amount_display": "25億円",
                "funding_sources": [
                    {"type": "general", "label": "決算剰余金・一般財源", "amount": "25億円 (100%)", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度9月補正予算概要 p.1",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000341/341201/R7_09hosei_gaiyo.pdf"
            },
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "過去負債計画的返済（公債償還基金計画外取崩しの計画返済）",
                "department": "行財政局財政部",
                "amount_jpy": 1000000000,
                "amount_display": "10億円",
                "funding_sources": [
                    {"type": "general", "label": "一般財源", "amount": "10億円 (100%)", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案概要 p.4",
                "doc_url": "https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000348/348991/R8_yosan_gaiyo.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和6年9月市会",
            "bill_number": "報12",
            "bill_title": "令和5年度京都市市公債特別会計歳入歳出決算の認定について",
            "result": "認定",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "反対"
            }
        },
        "milestone": {
            "date": "2024-08-01",
            "title": "2年連続の財政再生団体転落危機の完全回避確認",
            "status": "achieved"
        }
    },
    {
        "id": "P-10",
        "category": "文化政策",
        "headline": "「双京構想」推進・文化財修理拠点誘致",
        "stage_level": 2,
        "stage_label": "市公式計画化・国要望中",
        "election_promise": {
            "quote": "文化庁移転を契機とした『文化首都・京都』の確立。皇室機能の一部を京都で果たす双京構想の推進と文化財修復拠点の整備",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「文化首都・京都の飛躍」施策として位置づけ。文化庁との密接な連携のもと、皇室文化の継承発信と国立文化財修理センター機能の京都誘致を公式計画化。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和8年度 当初予算",
                "project_name": "文化財修理サイクルの確立に向けた修理助成制度再構築事業",
                "department": "文化市民局文化財保護課",
                "amount_jpy": 200000000,
                "amount_display": "2億円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税", "amount": "1億5,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "5,000万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和8年度予算案主要事業説明書（文化市民局）",
                "doc_url": "https://www.city.kyoto.lg.jp/bunshi/cmsfiles/contents/0000348/348991/R8_bunka_shuri.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-11-20",
            "title": "文部科学大臣に対する文化財保存修理体制強化に関する政策要望書の提出",
            "status": "achieved"
        }
    },
    {
        "id": "P-11",
        "category": "環境・美化",
        "headline": "観光地美化・スマートごみ箱・交通抑制",
        "stage_level": 3,
        "stage_label": "実証実験・配備中",
        "election_promise": {
            "quote": "観光混雑対策と美化の両立。パーク＆ライドの徹底、スマートごみ箱の増設による散乱ごみ対策",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「生活環境と調和した観光管理」施策に明記。主要観光地へのスマートごみ箱（SmaGO）の継続的配備とパーク＆ライド等の交通マネジメントを規定。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "スマートごみ箱（SmaGO）設置促進・美化受入環境整備事業",
                "department": "環境政策局適正処理施設部",
                "amount_jpy": 45000000,
                "amount_display": "4,500万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税", "amount": "3,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "1,500万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（環境政策局） p.9",
                "doc_url": "https://www.city.kyoto.lg.jp/kankyo/cmsfiles/contents/0000336/336421/R7_kankyo_smago.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-08-01",
            "title": "嵐山・清水・祇園エリアへのスマートごみ箱40基配備",
            "status": "achieved"
        }
    },
    {
        "id": "P-12",
        "category": "郊外再生",
        "headline": "洛西・向島ニュータウン等郊外再生",
        "stage_level": 3,
        "stage_label": "再生ビジョン推進中",
        "election_promise": {
            "quote": "郊外型大規模団地の再生。若者や子育て世帯が住みたくなるリノベーション支援とコミュニティ拠点整備",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「郊外拠点・ニュータウン再生プロジェクト」として公式策定。洛西SAIKOプロジェクト等の若者・子育て世帯向け居住・コミュニティ再生を位置づけ。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "こどもまんなか公園魅力アップ（洛西SAIKOプロジェクト推進分）",
                "department": "建設局みどり政策推進室",
                "amount_jpy": 87158000,
                "amount_display": "8,716万円",
                "funding_sources": [
                    {"type": "debt", "label": "市債", "amount": "4,500万円", "color": "bg-amber-50 text-amber-700 border-amber-200"},
                    {"type": "specific", "label": "国費", "amount": "2,500万円", "color": "bg-blue-50 text-blue-700 border-blue-200"},
                    {"type": "general", "label": "一般財源", "amount": "1,716万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（建設局） p.18",
                "doc_url": "https://www.city.kyoto.lg.jp/kensetu/cmsfiles/contents/0000336/336421/R7_kensetu_rakusai.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-07-01",
            "title": "洛西SAKAIBA共創拠点オープン",
            "status": "achieved"
        }
    },
    {
        "id": "P-13",
        "category": "文化・都市",
        "headline": "北山エリア文化交流拠点化・音楽祭",
        "stage_level": 2,
        "stage_label": "市公式計画化・協議中",
        "election_promise": {
            "quote": "植物園や京都コンサートホールを核とした北山エリアの文化・にぎわい創出。府立大学アリーナ計画の市民的合意形成と調和",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「北山文化ゾーンのにぎわい創出」施策に明記。植物園の自然環境と京都コンサートホール等の文化拠点を調和させた文化発信・音楽イベント構想を位置づけ。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "京都コンサートホール機能強化・北山エリア活性化検討事業",
                "department": "文化市民局文化芸術都市推進室",
                "amount_jpy": 28000000,
                "amount_display": "2,800万円",
                "funding_sources": [
                    {"type": "specific", "label": "宿泊税", "amount": "1,500万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "1,300万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（文化市民局） p.11",
                "doc_url": "https://www.city.kyoto.lg.jp/bunshi/cmsfiles/contents/0000336/336421/R7_bunshi_kitayama.pdf"
            }
        ],
        "legislative_bill": None,
        "milestone": {
            "date": "2024-12-01",
            "title": "府市北山エリア整備連絡会議の再開",
            "status": "achieved"
        }
    },
    {
        "id": "P-14",
        "category": "保健福祉",
        "headline": "精神障害者医療費支給・AYA世代支援",
        "stage_level": 4,
        "stage_label": "条例可決・助成開始",
        "election_promise": {
            "quote": "誰ひとり取り残さない共生社会。精神障害者医療費助成の通院対象拡大やAYA世代がん患者支援の実現",
            "source_name": "令和6年 京都市長選公報原本",
            "bulletin_url": "https://www.city.kyoto.lg.jp/senkyo/cmsfiles/contents/0000326/326065/kouhou.pdf"
        },
        "official_plan": {
            "date": "2026-03-01",
            "plan_name": "新京都戦略（令和8年3月改定）別綴 政策集",
            "summary": "「誰ひとり取り残さない共生福祉」重点項目に位置づけ。精神通院医療費助成の確実な運用と若年がん患者在宅療養支援の定着を公定計画化。",
            "doc_url": "https://www.city.kyoto.lg.jp/sogo/cmsfiles/contents/0000339/339369/seisakushuu2.pdf"
        },
        "budget_records": [
            {
                "fiscal_year": "令和7年度 当初予算",
                "project_name": "重度心身障害者医療費支給事業（精神障害者通院・入院対象拡充）",
                "department": "保健福祉局障害保健福祉推進室",
                "amount_jpy": 680000000,
                "amount_display": "6億8,000万円",
                "funding_sources": [
                    {"type": "specific", "label": "府補助金", "amount": "2億2,000万円", "color": "bg-indigo-50 text-indigo-700 border-indigo-200"},
                    {"type": "general", "label": "一般財源", "amount": "4億6,000万円", "color": "bg-slate-50 text-slate-700 border-slate-200"}
                ],
                "doc_source": "令和7年度主要事業説明書（保健福祉局） p.27",
                "doc_url": "https://www.city.kyoto.lg.jp/hokenfukushi/cmsfiles/contents/0000336/336421/R7_fukushi_seishin.pdf"
            }
        ],
        "legislative_bill": {
            "session_name": "令和6年11月市会",
            "bill_number": "議163",
            "bill_title": "京都市重度心身障害者等医療費支給条例の一部を改正する条例の制定について",
            "result": "可決",
            "party_votes": {
                "自民": "賛成",
                "公明": "賛成",
                "維新・京都・国民": "賛成",
                "共産": "賛成"
            }
        },
        "milestone": {
            "date": "2025-01-01",
            "title": "精神障害者通院医療費助成の拡充施行",
            "status": "achieved"
        }
    }
]

def calculate_summary_stats(pledges):
    total = len(pledges)
    enacted = sum(1 for p in pledges if p["stage_level"] == 4)
    bill_submitted = sum(1 for p in pledges if p.get("legislative_bill") and p["legislative_bill"].get("result") == "審議中")
    budgeted = sum(1 for p in pledges if p["stage_level"] == 3)
    official_plan_only = sum(1 for p in pledges if p["stage_level"] == 2)
    reviewing = sum(1 for p in pledges if p["stage_level"] == 1)

    total_amount = sum(
        sum(b["amount_jpy"] for b in p.get("budget_records", []))
        for p in pledges
    )

    return {
        "total_pledges": total,
        "stages": {
            "enacted": enacted,
            "bill_submitted": bill_submitted,
            "budgeted": budgeted,
            "official_plan_only": official_plan_only,
            "reviewing": reviewing
        },
        "total_allocated_budget_jpy": "104億1,316万円",
        "total_allocated_budget_raw": total_amount,
        "accommodation_tax_revenue_jpy": "132億円（令和8年度見込）",
        "debt_repayment_jpy": "年間35億円ペース堅持"
    }

def main():
    print("=== 京都市長（松井孝治）政策ライフサイクル×新京都戦略（確定版）トラッカー データ構築 ===")
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    summary_stats = calculate_summary_stats(PLEDGES_MASTER)

    output_data = {
        "mayor_info": MAYOR_INFO,
        "summary_stats": summary_stats,
        "pledges": PLEDGES_MASTER
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ 登録公約数: {summary_stats['total_pledges']} 項目")
    print(f"✓ 新京都戦略（確定版）連携: 14項目完了")
    print(f"✓ 公約関連投入予算総額: {summary_stats['total_allocated_budget_jpy']}")
    print(f"✓ 出力ファイル: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()