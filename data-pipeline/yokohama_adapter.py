import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class YokohamaAdapter:
    city_code = "yokohama"
    governing_body_id = 1249
    official_minute_url = "http://giji.city.yokohama.lg.jp/tenant/yokohama/MinuteView.html"

    # 行政幹部（苗字単体で出現する首長・副市長・教育長等）
    admin_names = {
        "山中", "平原", "城", "伊地知", "下田", "金高", "鯉渕", "大庭"
    }

    official_keywords = [
        "市長", "副市長", "局長", "区長", "部長", "室長", "課長", "次長", 
        "理事者", "教育長", "技監", "参事", "主査", "担当部長", "担当課長",
        "事務所長", "委員長", "会計管理者", "消防局長", "水道局長", "交通局長",
        "医療局長", "港湾局長", "建築局長", "都市整備局長", "道路局長", "政策局長",
        "総務局長", "財政局長", "市民局長", "こども青少年局長", "健康福祉局長",
        "みどり環境局長", "経済観光局長", "デジタル統括本部"
    ]

    procedural_phrases = [
        "お諮りいたします", "おはかりいたします", "御異議ございませんか", "ご異議ございませんか",
        "御異議ないものと認め", "ご異議ないものと認め", "さよう決定いたします",
        "これより委員会を開会", "これより本会議を開きます", "これより会議を開きます",
        "散会いたします", "休憩いたします", "再開いたします", "暫時休憩いたします",
        "説明を求めます", "説明を願います", "質疑を終了いたします", "質疑を終結いたします", "質疑を打ち切る",
        "審査を終了いたします", "発言を許します", "採決に入ります", "起立を求めます",
        "委員席につきましては", "正副委員長を代表いたしまして", "ただいま着席のとおり",
        "議題に供します", "一括議題に供します", "議題といたします", "議題とします",
        "報告願います", "報告を求めます", "発言の通告があります", "通告に従い"
    ]

    @classmethod
    def build_councilor_lookup(cls):
        master_path = PROJECT_ROOT / "frontend" / "public" / "data" / "yokohama_speaker_stats.json"
        if not master_path.exists():
            return {}, set()
        with open(master_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        fullnames, lookup = set(), {}
        for spk in data:
            name = (spk.get("speaker") or spk.get("name") or "").strip()
            if not name:
                continue
            clean_name = name.replace(" ", "").replace(" ", "")
            fullnames.add(name)
            fullnames.add(clean_name)
            lookup[name] = name
            lookup[clean_name] = name
        return lookup, fullnames

    @classmethod
    def fetch_data(cls, client):
        print(f"📥 [{cls.city_code.upper()}] BigQueryから横浜市会 全発言データを一括取得中 (2023-05-01以降)...")
        query = f"""
            SELECT 
                c.sequence_number,
                c.speaker_name AS speaker,
                c.comment AS statement_text,
                CAST(m.id AS STRING) AS meeting_id,
                m.name AS meeting_title,
                CAST(m.date AS STRING) AS meeting_date,
                COALESCE(m.url, '') AS official_url
            FROM `gen-lang-client-0253904061.sagebase_data.conversations` c
            JOIN `gen-lang-client-0253904061.sagebase_data.minutes` min ON c.minutes_id = min.id
            JOIN `gen-lang-client-0253904061.sagebase_data.meetings` m ON min.meeting_id = m.id
            JOIN `gen-lang-client-0253904061.sagebase_data.conferences` conf ON m.conference_id = conf.id
            WHERE conf.governing_body_id = {cls.governing_body_id}
              AND (m.name LIKE '%委員会%' OR m.name LIKE '%定例会%' OR m.name LIKE '%本会議%')
              AND m.name NOT LIKE '%市会運営%'
              AND m.name NOT LIKE '%初市会%'
              AND m.date >= '2023-05-01'
            ORDER BY m.date DESC, m.id ASC, c.sequence_number ASC
        """
        results = list(client.query(query).result())
        print(f"✅ [{cls.city_code.upper()}] 取得完了: 合計 {len(results):,} 件の発言レコード")
        return [dict(r) for r in results]

    @classmethod
    def build_threads(cls, stmts):
        print(f"🧵 [{cls.city_code.upper()}] 質疑スレッドを構築中...")
        lookup, fullnames = cls.build_councilor_lookup()

        def normalize_speaker(spk):
            clean = re.sub(r"(君|委員|議員)$", "", spk.strip()).strip()
            clean_no_space = clean.replace(" ", "").replace(" ", "")
            return lookup.get(clean_no_space, lookup.get(clean, clean))

        def is_admin(spk, text):
            clean_spk = spk.replace(" ", "").replace(" ", "")
            if clean_spk in cls.admin_names:
                return True
            if any(k in clean_spk for k in cls.official_keywords):
                return True
            spk_norm = normalize_speaker(spk)
            if spk_norm not in fullnames:
                if any(p in text[:60] for p in ["にお答えいたします", "にお答えします", "についてお答えします", "お尋ねいただきました"]):
                    return True
            return False

        def is_procedural(text):
            first_part = text[:150].replace(" ", "").replace(" ", "")
            return any(p in first_part for p in cls.procedural_phrases)

        meetings = {}
        for s in stmts:
            mid = s["meeting_id"]
            meetings.setdefault(mid, []).append(s)

        threads = []
        filtered_procedural = 0

        for mid, m_stmts in meetings.items():
            m_stmts = sorted(m_stmts, key=lambda x: x.get("sequence_number", 0))
            current_thread = None

            for s in m_stmts:
                spk = (s.get("speaker") or "").strip()
                text = (s.get("statement_text") or "").strip()
                if not spk or not text or "委員長" in spk or "議長" in spk:
                    continue

                if is_admin(spk, text):
                    if current_thread is not None:
                        current_thread["context_log"].append(f"【行政側 ({spk})】\n" + text)
                        current_thread["has_response"] = True
                else:
                    spk_norm = normalize_speaker(spk)
                    if spk_norm in fullnames:
                        if is_procedural(text):
                            filtered_procedural += 1
                            continue

                        if current_thread is None or current_thread["speaker"] != spk_norm:
                            if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                                threads.append(current_thread)
                            current_thread = {
                                "thread_id": f"th_{mid}_{s['sequence_number']}",
                                "speaker": spk_norm,
                                "meeting_id": mid,
                                "meeting_title": s["meeting_title"],
                                "meeting_date": str(s["meeting_date"]),
                                "question_text": text,
                                "context_log": [f"【議員 ({spk_norm})】\n" + text],
                                "has_response": False,
                                "official_url": s.get("official_url") or cls.official_minute_url
                            }
                        else:
                            current_thread["context_log"].append(f"【議員 ({spk_norm})】\n" + text)
                            if len(current_thread["question_text"]) < 200:
                                current_thread["question_text"] += "\n" + text

            if current_thread is not None and current_thread["has_response"] and len(current_thread["question_text"]) > 40:
                threads.append(current_thread)

        print(f"🧹 [{cls.city_code.upper()}] 除外された進行発言: {filtered_procedural:,} 件")
        print(f"✅ [{cls.city_code.upper()}] {len(threads):,} 件の政策質疑スレッドを構築しました。")
        return threads
