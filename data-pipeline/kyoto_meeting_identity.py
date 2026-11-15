"""Pure Kyoto meeting identity checks shared by acquisition and saved replay."""
import re
import unicodedata
from datetime import date
from html import unescape

TERM_START = "2023-05-01"

def norm(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))

def target(review):
    if review.get("city") != "kyoto" or review.get("source_kind") != "meeting":
        raise ValueError("Kyoto meeting evidence required; materials are not meetings")
    for key in ("council_id", "schedule_id"):
        if type(review.get(key)) not in (str, int) or not re.fullmatch(r"[1-9][0-9]*", str(review[key])):
            raise ValueError("Unambiguous official council and schedule identifiers required")
    value = review.get("meeting_date", "")
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Official calendar date required")
    day = date.fromisoformat(value)
    if day < date.fromisoformat(TERM_START):
        raise ValueError("Meeting outside current Kyoto term")
    name = norm(review.get("formal_name"))
    m = re.fullmatch(r"令和(\d+)年(\d+)月(.+)\(第(\d+)回\)", name)
    if not m or type(review.get("round")) is not int or review["round"] < 1:
        raise ValueError("Formal committee name and round required")
    if (int(m[1])+2018, int(m[2]), m[3], int(m[4])) != (day.year, day.month, norm(review.get("committee")), review["round"]):
        raise ValueError("Formal name/date/round conflict")
    return dict(review, council_id=str(review["council_id"]), schedule_id=str(review["schedule_id"]))

def schedule(review, selected):
    t = target(review)
    day = date.fromisoformat(t["meeting_date"])
    m = re.fullmatch(r"(\d{1,2})月(\d{1,2})日[-ー](\d+)号", norm(selected.get("name")))
    if (not m or tuple(map(int, m.groups())) != (day.month, day.day, t["round"])
            or selected.get("meeting_date") != t["meeting_date"]
            or str(selected.get("schedule_id")) != t["schedule_id"]
            or selected.get("meeting_key") != "kyoto:"+t["council_id"]+":"+t["schedule_id"]):
        raise ValueError("Official schedule date, round or identifiers conflict")

def opening(review, blocks):
    t = target(review)
    if not blocks or str(blocks[0].get("minute_id")) != "1" or norm(blocks[0].get("title")) != "開会":
        raise ValueError("Official opening block missing")
    text = unescape(re.sub(r"<[^>]+>", "", blocks[0].get("body", "")))
    lines = [norm(x) for x in text.splitlines() if norm(x)]
    if (len(lines) < 3 or lines[0] != norm(t["formal_name"])
            or lines[1] != "第"+str(t["round"])+"回"+norm(t["committee"])+"記録"):
        raise ValueError("Opening formal name/round mismatch")
    m = re.fullmatch(r"[◯○]令和(\d+)年(\d+)月(\d+)日\([月火水木金土日]\)", lines[2])
    day = date.fromisoformat(t["meeting_date"])
    if not m or (int(m[1])+2018, int(m[2]), int(m[3])) != (day.year, day.month, day.day):
        raise ValueError("Opening calendar date mismatch")
    return {"identity_confirmed": True, "opening_position": "tenant_minutes[0].body:first3_nonempty_lines", "official_coverage": "unknown"}
