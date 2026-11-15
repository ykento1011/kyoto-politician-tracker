"""Offline Nagoya roster HTML extraction. No scraper import, requests or writes."""
import re
import unicodedata
from html.parser import HTMLParser


def name_key(value):
    # Same NFKC/space rule as scrape_councilors_master.clean_name.
    # Do not collapse kanji variants or infer person identity.
    return re.sub(r"[\s\u3000]+", "", unicodedata.normalize("NFKC", value))


class Node:
    def __init__(self, tag, attrs, parent, line):
        self.tag, self.attrs, self.parent, self.line = tag, dict(attrs), parent, line
        self.children = []

    def text(self):
        return "".join(c.text() if isinstance(c, Node) else c for c in self.children)

    def path(self):
        if self.parent is None:
            return ""
        peers = [c for c in self.parent.children if isinstance(c, Node) and c.tag == self.tag]
        return self.parent.path() + "/" + self.tag + "[" + str(peers.index(self) + 1) + "]"


class Tree(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [], None, 1)
        self.stack = [self.root]
        self.nodes = []
        self.feed(body.decode("utf-8-sig"))
        self.close()

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.stack[-1], self.getpos()[0])
        self.stack[-1].children.append(n)
        self.nodes.append(n)
        if tag == "br":
            n.children.append("\n")
        if tag not in {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "base", "embed", "param"}:
            self.stack.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def article_nodes(self):
        roots = [n for n in self.nodes if n.tag == "article" and n.attrs.get("id") == "content"]
        if len(roots) != 1:
            raise ValueError("Official article structure missing")
        root = roots[0]
        def inside(n):
            while n:
                if n is root:
                    return True
                n = n.parent
            return False
        return [n for n in self.nodes if inside(n) and n.attrs.get("id") != "reference"]


def source_position(node):
    return {"dom": node.path(), "line": node.line, "literal": node.text().strip()}


def parse_roster(body, edition):
    """Return observations, never membership/role events or confirmed identities."""
    nodes = Tree(body).article_nodes()
    rows, group, district, role = [], None, None, None
    declared = {}
    for n in nodes:
        if n.attrs.get("id") == "reference" or n.tag == "h2" and "お問い合わせ" in n.text():
            break
        txt = n.text().strip()
        if edition == "initial_186":
            if n.tag == "h2":
                if txt == "会派の主な役員":
                    break
                m = re.fullmatch(r"(.+区)[(（](\d+)人[)）]", txt)
                district = m[1] if m else None
                if m:
                    declared[district] = int(m[2])
            if n.tag == "strong" and district:
                m = re.fullmatch(r"(.+?)[(（](.+?)[)）]", txt)
                if not m:
                    raise ValueError("Unexpected initial roster row")
                rows.append(dict(name=m[1].strip(), district=district, group=m[2],
                                 roles=[], position=source_position(n)))
        elif edition == "factions_20260521":
            if n.tag == "h2":
                m = re.fullmatch(r"(.+)[(（](\d+)人[)）]", txt)
                group = m[1] if m else None
                if m:
                    declared[group] = int(m[2])
            if n.tag == "dt":
                role = txt
            if n.tag == "dd" and group:
                for value in txt.splitlines():
                    if value.strip():
                        rows.append(dict(name=value.strip(), district=None, group=group,
                                         roles=[{"scope": "faction:" + group, "title": role}],
                                         position=source_position(n)))
        else:
            raise ValueError("Unsupported saved page edition")
    if len(rows) != 68 or sum(declared.values()) != 68:
        raise ValueError("Incomplete/changed roster: hold, never infer departures")
    field = "district" if edition == "initial_186" else "group"
    for key, count in declared.items():
        if sum(r[field] == key for r in rows) != count:
            raise ValueError("Official section/member count mismatch")
    if len({name_key(r["name"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate/homonymous names require explicit review")
    return rows

