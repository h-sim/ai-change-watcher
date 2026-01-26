# normalizers.py
import re
import xml.etree.ElementTree as ET
import html


def _norm_ws(s: str) -> str:
    s = s or ""
    s = s.replace("\u200b", "")  # zero-width
    s = re.sub(r"\s+", " ", s).strip()
    return s


# --- RSS/Atom minimal normalization helpers ---

def _clean_xml_for_et(xml_text: str) -> str:
    """ElementTree が落ちやすい不正文字・裸の & を最低限だけ補正する。"""
    s = xml_text or ""
    # XML 1.0 で禁止される制御文字を除去（\t \n \r は残す）
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
    # 裸の & を &amp; に（既に正しい entity は保持）
    s = re.sub(r"&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]+;)", "&amp;", s)
    return s


def _strip_tags(s: str) -> str:
    s = s or ""
    s = re.sub(r"<[^>]+>", " ", s)
    return s


def _extract_tag_text(block: str, tag: str) -> str:
    """<tag>...</tag> の中身を抽出（CDATA/HTML entity/タグ除去込み）"""
    if not block:
        return ""
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    txt = m.group(1)
    # CDATA除去（全体がCDATAのときのみ）
    txt = re.sub(r"^\s*<!\[CDATA\[(.*)\]\]>\s*$", r"\1", txt, flags=re.DOTALL)
    txt = html.unescape(txt)
    txt = _strip_tags(txt)
    return _norm_ws(txt)


def _extract_atom_link_href(block: str) -> str:
    """Atomの <link ... href=...> を優先して抽出"""
    if not block:
        return ""
    # rel="alternate" のhref
    m = re.search(r"<link[^>]*rel=\"alternate\"[^>]*href=\"([^\"]+)\"[^>]*/?>", block, flags=re.IGNORECASE)
    if m:
        return _norm_ws(html.unescape(m.group(1)))
    # rel無しのhref
    m = re.search(r"<link[^>]*href=\"([^\"]+)\"[^>]*/?>", block, flags=re.IGNORECASE)
    if m:
        return _norm_ws(html.unescape(m.group(1)))
    return ""


def _normalize_rss_min_fallback(xml_text: str, body_limit: int = 5000, max_items: int = 200) -> str:
    """壊れたXMLでも、regexで item/entry を拾って最小限の正規化を行う"""
    text = xml_text or ""
    items = []

    # RSS <item>...</item>
    for block in re.findall(r"<item\b.*?>.*?</item>", text, flags=re.IGNORECASE | re.DOTALL)[:max_items]:
        title = _extract_tag_text(block, "title")
        link = _extract_tag_text(block, "link")
        guid = _extract_tag_text(block, "guid")
        pub = _extract_tag_text(block, "pubDate")
        desc = _extract_tag_text(block, "description")
        items.append({
            "title": title,
            "link": link,
            "id": guid,
            "date": pub,
            "body": desc,
        })

    # Atom <entry>...</entry>
    for block in re.findall(r"<entry\b.*?>.*?</entry>", text, flags=re.IGNORECASE | re.DOTALL)[:max_items]:
        title = _extract_tag_text(block, "title")
        link = _extract_atom_link_href(block) or _extract_tag_text(block, "link")
        eid = _extract_tag_text(block, "id")
        updated = _extract_tag_text(block, "updated") or _extract_tag_text(block, "published")
        summary = _extract_tag_text(block, "summary")
        content = _extract_tag_text(block, "content")
        body = summary or content
        items.append({
            "title": title,
            "link": link,
            "id": eid,
            "date": updated,
            "body": body,
        })

    items.sort(key=lambda x: (x.get("link", ""), x.get("id", ""), x.get("title", "")))

    out_lines = []
    for it in items:
        out_lines.append("#ITEM")
        out_lines.append(f"title: {it.get('title','')}")
        out_lines.append(f"link: {it.get('link','')}")
        out_lines.append(f"id: {it.get('id','')}")
        out_lines.append(f"date: {it.get('date','')}")
        body = it.get("body", "")
        body = body[:body_limit] if body_limit and body else ""
        out_lines.append(f"body: {body}")

    return "\n".join(out_lines).strip() + "\n"


def normalize_rss_min(xml_text: str, body_limit: int = 5000) -> str:
    """
    RSS/Atomの「安定して比較したい部分」だけを抽出して整形する。
    フィード全体のlastBuildDate等の揺れでは差分が出ないようにする。

    取得元が不正なXML（無効文字 / 裸の&等）を返すことがあるため、
    まず軽い補正をかけてElementTreeでパースし、だめならregexでフォールバックする。
    """
    xml_text = xml_text or ""

    # 1) まずはそのままパースを試す
    root = None
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        pass

    # 2) 失敗したら軽い補正をかけて再試行
    if root is None:
        try:
            cleaned = _clean_xml_for_et(xml_text)
            root = ET.fromstring(cleaned)
        except Exception:
            root = None

    # 3) それでもダメならフォールバック
    if root is None:
        return _normalize_rss_min_fallback(xml_text, body_limit=body_limit)

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []

    # RSS2: channel/item
    for item in root.findall(".//channel/item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        guid = item.findtext("guid") or ""
        pub = item.findtext("pubDate") or ""
        desc = item.findtext("description") or ""
        items.append({
            "title": _norm_ws(title),
            "link": _norm_ws(link),
            "id": _norm_ws(guid),
            "date": _norm_ws(pub),
            "body": _norm_ws(desc),
        })

    # Atom: feed/entry
    for entry in root.findall(".//atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)

        link = ""
        for lk in entry.findall("atom:link", ns):
            if lk.attrib.get("rel", "alternate") == "alternate":
                link = lk.attrib.get("href", "")
                break

        eid = entry.findtext("atom:id", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)
        summary = entry.findtext("atom:summary", default="", namespaces=ns)
        content = entry.findtext("atom:content", default="", namespaces=ns)
        body = summary or content or ""

        items.append({
            "title": _norm_ws(title),
            "link": _norm_ws(link),
            "id": _norm_ws(eid),
            "date": _norm_ws(updated),
            "body": _norm_ws(body),
        })

    # 順序の揺れ対策（リンク→id→title）
    items.sort(key=lambda x: (x["link"], x["id"], x["title"]))

    out = []
    for it in items:
        out.append("#ITEM")
        out.append(f"title: {it['title']}")
        out.append(f"link: {it['link']}")
        out.append(f"id: {it['id']}")
        out.append(f"date: {it['date']}")
        body = it["body"][:body_limit] if body_limit and it["body"] else ""
        out.append(f"body: {body}")

    return "\n".join(out).strip() + "\n"


def normalize_openapi_c14n_v1(yaml_text: str) -> str:
    """OpenAPI YAMLを『意味を変えずに安定した文字列』へ正規化する。"""
    yaml_text = yaml_text or ""

    try:
        import yaml  # PyYAML
    except Exception:
        return yaml_text

    try:
        obj = yaml.safe_load(yaml_text)
    except Exception:
        return yaml_text

    # serversの順序を安定化（代表的ノイズ）
    if isinstance(obj, dict) and isinstance(obj.get("servers"), list):
        try:
            obj["servers"] = sorted(
                obj["servers"],
                key=lambda s: ((s or {}).get("url", ""), str(s))
            )
        except Exception:
            pass

    import json
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"