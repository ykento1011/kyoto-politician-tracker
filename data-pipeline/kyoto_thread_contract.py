"""Kyoto saved-SSP speaker and thread contract. Pure: no I/O or API calls."""
import hashlib
import html
import json
import re
import unicodedata

REVISION = "kyoto-ssp-agenda-v2"
COUNCIL_ROLES = {"委員", "議員", "委員長", "副委員長", "分科会長", "副分科会長", "議長", "副議長", "主査", "副主査"}
BOUNDARY = re.compile(
    r"以上で.{0,70}(?:終わ|終え|終了)|(?:次の|それでは).{0,100}(?:審査|報告聴取|関係の|関係を)"
    r"|(?:暫時|ここで|それでは).{0,20}休憩|委員会を再開|散会"
    r"|取扱いはいかが|表決を採|採決を行|討論に入"
)

def compact(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))

def person(value):
    name = compact(value)
    m = re.fullmatch(r"(.+?)\(([^()]+)\)", name)
    return (m.group(2), m.group(1)) if m else (name, "")

def master_names(master):
    aliases = {}
    for row in master:
        canonical = compact(row.get("name"))
        if not canonical:
            raise ValueError("Empty councilor name")
        for name in [row["name"], *row.get("aliases", [])]:
            alias = compact(name)
            if alias in aliases and aliases[alias] != canonical:
                raise ValueError("Ambiguous councilor alias")
            aliases[alias] = canonical
    return aliases

def classify(row, source, aliases):
    name, role = person(source.get("title"))
    parsed_name, _ = person(row.get("speaker"))
    if not name or name != parsed_name:
        return dict(kind="unknown", reason="Source/parsed speaker mismatch")
    code = source.get("minute_type_code")
    if code == 5 and role in COUNCIL_ROLES and name in aliases:
        return dict(kind="councilor", canonical=aliases[name], original_title=source["title"])
    if code == 4 and role in COUNCIL_ROLES and name in aliases:
        return dict(kind="procedure", canonical=aliases[name], original_title=source["title"])
    if code == 6 and role and role not in COUNCIL_ROLES and name not in aliases:
        return dict(kind="administration", canonical=name, original_title=source["title"])
    return dict(kind="unknown", reason="Unconfirmed or conflicting official role/master")

def source_boundary(source):
    if source.get("minute_type_code") != 4:
        return False
    text = html.unescape(re.sub(r"<[^>]+>", "", source.get("body", "")))
    return bool(BOUNDARY.search(re.sub(r"\s+", "", text)))


def petition_transitions(source, aliases):
    """Require a known chair's formal transition and the following official explanation.

    Inspect original blocks, including chair rows omitted by the speech parser.
    A numbered agenda mention inside a question/answer is not a transition.
    """
    evidence, holds = {}, []
    ordered = sorted(source)
    for i, seq in enumerate(ordered):
        block = source[seq]
        name, role = person(block.get("title"))
        if block.get("minute_type_code") != 4 or name not in aliases or role not in COUNCIL_ROLES:
            continue
        text = compact(html.unescape(re.sub(r"<[^>]+>", "", block.get("body", ""))))
        switch = re.search(r"次に[、,]?陳情第(\d+)号.{0,160}審査(?:を)?いたします", text)
        if not switch:
            continue
        following = next((source[n] for n in ordered[i+1:] if source[n].get("minute_type_code") != 4), None)
        if following is None:
            holds.append(dict(sequence=seq, reason="Agenda transition has no following official explanation"))
            continue
        next_name, next_role = person(following.get("title"))
        explanation = compact(html.unescape(re.sub(r"<[^>]+>", "", following.get("body", ""))))
        if (following.get("minute_type_code") != 6 or not next_role or next_role in COUNCIL_ROLES
                or next_name in aliases or not re.search(r"陳情第"+switch.group(1)+r"号.{0,180}御説明", explanation)):
            holds.append(dict(sequence=seq, reason="Agenda transition/explanation identity cannot be confirmed"))
            continue
        evidence[seq] = dict(chair_title=block["title"], petition_number=switch.group(1),
                             explanation_sequence=following["minute_id"])
    return evidence, holds

def build(rows, blocks, master, is_procedural_call):
    if not rows:
        raise ValueError("Empty Kyoto input")
    aliases = master_names(master)
    source = {}
    for block in blocks:
        seq = block.get("minute_id")
        if type(seq) is not int or seq in source:
            raise ValueError("Duplicate/invalid original position")
        source[seq] = block
    meeting_ids = {r.get("meeting_id") for r in rows}
    if len(meeting_ids) != 1 or not re.fullmatch(r"ssp_[1-9][0-9]*_[1-9][0-9]*", next(iter(meeting_ids)) or ""):
        raise ValueError("One explicit SSP meeting required")
    sequences = [r.get("sequence_number") for r in rows]
    if any(type(s) is not int or s not in source for s in sequences) or len(set(sequences)) != len(rows):
        raise ValueError("Duplicate/missing parsed original position")
    rows = sorted(rows, key=lambda r:r["sequence_number"])
    roles = {r["sequence_number"]:classify(r, source[r["sequence_number"]], aliases) for r in rows}
    transitions, holds = petition_transitions(source, aliases)
    breaks = sorted({s for s,b in source.items() if source_boundary(b)} | set(transitions))
    threads = []
    current = None
    previous = 0
    def finish():
        nonlocal current
        if current is not None:
            threads.append(current)
            current = None
    for row in rows:
        seq = row["sequence_number"]
        # A boundary remains effective even if the legacy parser omitted that chair row.
        if any(previous < stop < seq for stop in breaks):
            finish()
        previous = seq
        role = roles[seq]
        text = str(row.get("statement_text", "")).strip()
        raw_speaker = row["speaker"]
        if role["kind"] == "unknown":
            holds.append(dict(sequence=seq, reason=role["reason"]))
            finish()
            continue
        if role["kind"] == "procedure":
            if current is not None:
                current["related_statements"].append(row)
            if seq in breaks:
                finish()
            continue
        if role["kind"] == "councilor":
            if current is not None and current["councilor_key"] != role["canonical"]:
                finish()
            if is_procedural_call(text):
                if current is not None:
                    current["related_statements"].append(row)
                continue
            if current is None:
                current = dict(speaker=raw_speaker, councilor_key=role["canonical"],
                    meeting_id=row["meeting_id"], meeting_title=row["meeting_title"],
                    meeting_date=row["meeting_date"], main_statement=row,
                    context_log=[f"【議員 ({raw_speaker})】\n{text}"],
                    related_statements=[row], prompt_statement_ids=[row["id"]], has_admin_response=False)
            else:
                current["context_log"].append(f"【議員・再質問 ({raw_speaker})】\n{text}")
                current["related_statements"].append(row)
                current["prompt_statement_ids"].append(row["id"])
        elif current is not None:
            current["related_statements"].append(row)
            if not is_procedural_call(text):
                current["has_admin_response"] = True
                current["context_log"].append(f"【行政側・答弁 ({raw_speaker})】\n{text}")
                current["prompt_statement_ids"].append(row["id"])
    finish()
    included = []
    for t in threads:
        for row in t["related_statements"]:
            seq = row["sequence_number"]
            role = roles[seq]
            if role["kind"] == "unknown" or (role["kind"] == "councilor" and role["canonical"] != t["councilor_key"]):
                raise ValueError("Cross-speaker or unknown attribution")
            included.append(seq)
    if len(set(included)) != len(included):
        raise ValueError("Statement assigned to multiple threads")
    return dict(revision=REVISION, threads=threads, roles=roles, holds=holds,
                boundary_positions=breaks, agenda_evidence=transitions)

def thread_key(thread):
    row = thread["main_statement"]
    return str(row["meeting_id"]) + "_" + str(row["sequence_number"])

def fingerprint(ns, thread):
    """Capture exactly the legacy prompt/config, bypassing its retry handler."""
    class Captured(BaseException):
        pass
    saved = {}
    class Capture:
        def generate_content(self, prompt, generation_config):
            saved.update(prompt=prompt, config=generation_config)
            raise Captured()
    previous = ns["model"]
    ns["model"] = Capture()
    try:
        ns["evaluate_thread_with_gemini"](thread)
    except Captured:
        pass
    finally:
        ns["model"] = previous
    if not saved:
        raise ValueError("Legacy prompt capture failed")
    return dict(speaker=thread["speaker"],
        statement_ids=[r["id"] for r in thread["related_statements"]],
        prompt_statement_ids=thread["prompt_statement_ids"],
        prompt_sha256=hashlib.sha256(saved["prompt"].encode()).hexdigest(),
        config=saved["config"])

def timeline(threads, roles):
    result = {}
    for thread in threads:
        target = thread["main_statement"]["sequence_number"]
        result[str(target)] = [
            dict(sequence_number=r["sequence_number"], speaker=r["speaker"].strip(),
                 statement_text=r["statement_text"].strip(), is_target=r["sequence_number"]==target,
                 is_admin=roles.get(str(r["sequence_number"]),roles.get(r["sequence_number"]))["kind"]=="administration",
                 is_short_procedural=roles.get(str(r["sequence_number"]),roles.get(r["sequence_number"]))["kind"]=="procedure")
            for r in thread["related_statements"]]
    return result
