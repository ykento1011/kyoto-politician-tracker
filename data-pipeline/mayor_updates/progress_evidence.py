"""Offline progress checks. A vote JSON match alone is not source authentication."""
import re
import unicodedata
from urllib.parse import urlsplit
from .projection import Hold, budget_total, format_amount

FIELDS = ("city_code", "session_year", "session_name", "bill_number", "bill_title", "source_url")
LABELS = {"preparation": "導入準備（予算案確認）", "hold": "議決根拠を確認中"}


def bill_identity(record, city, allowed_hosts):
    if any(not record.get(k) for k in FIELDS):
        raise Hold("Incomplete legislative identity")
    if record["city_code"] != city or type(record["session_year"]) is not int:
        raise Hold("Wrong city or session year")
    # Calendar year of the meeting, NOT the budget fiscal year or URL directory.
    match = re.fullmatch(r"令和(元|[0-9]+)年([0-9]+)月市会", record["session_name"])
    if not match or 2018 + (1 if match[1] == "元" else int(match[1])) != record["session_year"]:
        raise Hold("Session year mismatch")
    u = urlsplit(record["source_url"])
    if (u.scheme != "https" or u.netloc not in allowed_hosts or
            u.username or u.password or u.query or u.fragment):
        raise Hold("Noncanonical official source URL")
    def norm(value):
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)))
    return tuple(norm(record[k]) for k in FIELDS)


def legislative_match(registered, official, city, allowed_hosts):
    """Caller must supply a source-reviewed record, not just a scraped row."""
    try:
        key = bill_identity(registered, city, allowed_hosts)
        matches = [r for r in official if bill_identity(r, city, allowed_hosts) == key]
        return (len(matches) == 1 and matches[0].get("verification_status") == "source_checked"
                and registered.get("result") == matches[0].get("result")
                and bool(matches[0].get("result")))
    except (Hold, ValueError, TypeError):
        return False


def validate_progress(data, official_votes=()):
    """Reject drift; never promote, demote, rewrite facts or recalculate in place."""
    rows = data["pledges"]
    for p in rows:
        review = p.get("progress_evidence")
        if not review:
            continue  # Untouched legacy policies keep their existing contract.
        status = review.get("status")
        if status not in LABELS or p.get("stage_label") != LABELS[status] or not review.get("summary"):
            raise Hold("Progress label/review mismatch")
        if status == "preparation" and p.get("stage_level") != 3:
            raise Hold("Preparation cannot assert enactment")
        b = p.get("legislative_bill")
        if b:
            matched = legislative_match(b, official_votes, "kyoto", {"www2.city.kyoto.lg.jp"})
            if not matched and b.get("verification_status") != "hold":
                raise Hold("Unresolved legislative record must remain held")
            if b.get("verification_status") != "hold" or not b.get("verification_note"):
                raise Hold("Review decision required before lifting progress hold")
        m = p.get("milestone")
        if m and (m.get("verification_status") != "unverified" or
                  m.get("policy_relation") not in {"contextual", "unconfirmed"} or
                  not m.get("verification_note")):
            raise Hold("Unverified milestone cannot become policy implementation")

    stages = dict(enacted=sum(p["stage_level"] == 4 for p in rows),
                  bill_submitted=sum(p.get("legislative_bill", {}).get("result") == "審議中"
                                     for p in rows if p.get("legislative_bill")),
                  budgeted=sum(p["stage_level"] == 3 for p in rows),
                  official_plan_only=sum(p["stage_level"] == 2 for p in rows),
                  reviewing=sum(p["stage_level"] == 1 for p in rows))
    stats = data["summary_stats"]
    if stats["total_pledges"] != len(rows) or stats["stages"] != stages:
        raise Hold("Registered stage summary is stale")
    progress = [k for k in data["kpis"] if k["label"] == "公約推進・予算化率"]
    count = sum(p["stage_level"] >= 3 for p in rows)
    if (not rows or len(progress) != 1 or progress[0]["value"] != f"{count/len(rows)*100:.1f}%"
            or progress[0]["subtext"] != f"{count}/{len(rows)}事業で予算措置・成立"):
        raise Hold("Registered progress KPI is stale")
    total = budget_total(rows)
    amounts = [k for k in data["kpis"] if k["label"] == "関連予算措置総額"]
    if (stats["total_allocated_budget_raw"] != total or
            stats["total_allocated_budget_jpy"] != format_amount(total) or
            len(amounts) != 1 or amounts[0]["value"] != format_amount(total)):
        raise Hold("Budget aggregate is stale")
    return True
