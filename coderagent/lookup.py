"""一个资料工具：先查知识库，没有再联网，并把页面写回笔记。"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Optional
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from coderagent.extract import extract
from coderagent.load import load_corpus, parse_source_text
from coderagent.models import Evidence, Source

Search = Callable[[str], Optional[tuple]]
SEARCH_URL = "https://www.bing.com/search"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Lookup:
    found: bool
    origin: str
    notes: tuple[Source, ...]
    evidence: tuple[Evidence, ...]
    rejected: tuple[str, ...]
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "found": self.found,
            "origin": self.origin,
            "reason": self.reason,
            "notes": [{"id": note.id, "title": note.title, "path": note.path} for note in self.notes],
            "evidence": [
                {
                    "id": item.id,
                    "option": item.option,
                    "dimension": item.dimension,
                    "quote": item.quote,
                }
                for item in self.evidence
            ],
        }


CLOSE_ENOUGH = 0.55


def lookup(
    corpus_dir: Path,
    query: str,
    option: str,
    search: Search,
    knowledge=None,
    question: str = "",
) -> Lookup:
    query = query.strip()
    option = option.strip()
    if not query or not option:
        return _empty("query 和 option 都不能为空。")
    if "," in option or "\n" in option:
        return _empty("option 不能包含逗号或换行。")
    remembered = _from_knowledge(knowledge, corpus_dir, option, question)
    if remembered is not None:
        return remembered
    page = search(option, option)
    if page is None:
        return _empty("知识库没有够近的段落，联网也没有拿到可用正文。")
    title, text, url = _take_page(page)
    written = _write_note(corpus_dir, option, title, text, url)
    if written is None:
        return _empty("联网页面里没有可用的原句。")
    if knowledge is not None:
        knowledge.add_source(written)
    evidence, rejected = extract((written,))
    if evidence:
        return Lookup(True, "web", (written,), evidence, rejected)
    remembered = _from_knowledge(knowledge, corpus_dir, option, question)
    if remembered is not None:
        return remembered
    return _empty("联网页面已写入知识库，但没有可引用的原句。")


def search_web(query: str, option: str = "") -> tuple[str, str] | None:
    term = (option or query).strip()
    _log("--- 联网搜索 ---", f"query: {query}", f"实际检索：{term}")
    html = _get(SEARCH_URL + "?" + urllib.parse.urlencode({"q": term, "setlang": "zh-Hans"}))
    if not html:
        _log("搜索页没有返回")
        return None
    links = _result_links(html)[:5]
    if not links:
        _log("搜索页里没有结果链接")
        return None
    _log("结果链接：", *[f"- {url}" for url in links])
    for url in links:
        page = _get(url)
        if not page:
            _log(f"打开失败：{url}")
            continue
        title, text = _page_text(page)
        if len(text) < 80:
            _log(f"正文太短：{url}")
            continue
        if term.casefold() not in text.casefold():
            _log(f"页面未提到 {term}：{url}")
            continue
        kept = text[:4000]
        _log(f"采用：{title or term}", url, kept)
        return title or term, kept, url
    _log("没有拿到可用正文")
    return None


def _log(*lines: str) -> None:
    print("\n".join(lines), file=sys.stderr)


def _result_links(html: str) -> list[str]:
    hrefs = re.findall(r'<h2\b[^>]*>\s*<a\b[^>]*href="([^"]+)"', html, re.I)
    links = []
    for href in hrefs:
        url = unescape(href)
        host = urllib.parse.urlparse(url).netloc.casefold()
        if not url.startswith(("http://", "https://")):
            continue
        if host.endswith("bing.com") or host.endswith("microsoft.com"):
            continue
        if url not in links:
            links.append(url)
    return links


def _page_text(html: str) -> tuple[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = _plain(title_match.group(1)) if title_match else ""
    without = re.sub(r"(?is)<(script|style|noscript)\b.*?>.*?</\1>", " ", html)
    return title, _plain(without)


def _plain(html: str) -> str:
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _get(url: str) -> str | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(500_000)
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def _from_knowledge(knowledge, corpus_dir: Path, option: str, question: str = "") -> Lookup | None:
    """用用户的原问题做向量检索。段落里仍要出现选项名。"""
    if knowledge is None:
        return None
    knowledge.index_corpus(corpus_dir)
    asked = question.strip() or option
    hits = [
        hit
        for hit in knowledge.search(asked, limit=12)
        if hit.score >= CLOSE_ENOUGH and option.casefold() in hit.text.casefold()
    ][:4]
    if not hits:
        _log(f"知识库没有够近的段落：{option}")
        return None
    by_path = {source.path: source for source in load_corpus(corpus_dir)}
    notes: list[Source] = []
    evidence: list[Evidence] = []
    for hit in hits:
        source = by_path.get(hit.path)
        if source is None or hit.text not in source.body:
            continue
        if source.id not in {note.id for note in notes}:
            notes.append(source)
        evidence.append(
            Evidence(
                id=f"{source.id}-{hit.start}",
                source_id=source.id,
                option=option,
                dimension="资料原句",
                stance="info",
                quote=hit.text,
            )
        )
    if not evidence:
        return None
    _log(f"知识库命中：{option}，{len(evidence)} 段")
    return Lookup(True, "knowledge", tuple(notes), tuple(evidence), ())


def _take_page(page) -> tuple[str, str, str]:
    title, text = page[0], page[1]
    url = page[2] if len(page) > 2 else ""
    return title, text, url


def _write_note(corpus_dir: Path, option: str, title: str, text: str, url: str = "") -> Source | None:
    url = url.replace("\n", "").replace("\r", "").strip()
    body = re.sub(r"\s+", " ", text).strip()[:4000]
    if option.casefold() not in body.casefold():
        return None
    sentences = _sentences(body, option)
    slug = _slug(option)
    note_id = f"web-{slug}"
    title = title.replace("\n", " ").replace("\r", " ").strip() or option
    blocks = []
    for index, sentence in enumerate(sentences, start=1):
        blocks.append(
            "\n".join(
                [
                    "```evidence",
                    f"id: {note_id}-{index}",
                    f"option: {option}",
                    "dimension: 资料原句",
                    "stance: info",
                    f"quote: {sentence}",
                    "```",
                ]
            )
        )
    raw = (
        "---\n"
        f"id: {note_id}\n"
        f"title: {title}\n"
        f"tags: {option}\n"
        + (f"url: {url}\n" if url else "")
        + "---\n\n"
        f"{body}\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )
    path = corpus_dir / f"{note_id}.md"
    path.write_text(raw, encoding="utf-8")
    relative = path.relative_to(corpus_dir.parent).as_posix()
    return parse_source_text(raw, relative)


def _sentences(body: str, option: str) -> list[str]:
    needle = option.casefold()
    found = []
    for piece in re.split(r"(?<=[。！？.!?])", body):
        sentence = piece.strip()
        if needle not in sentence.casefold():
            continue
        if 16 <= len(sentence) <= 180 and "```" not in sentence and sentence in body:
            found.append(sentence)
        if len(found) == 8:
            break
    return found


def _slug(option: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", option.casefold()).strip("-")
    return slug or "note"


def _empty(reason: str) -> Lookup:
    return Lookup(False, "none", (), (), (), reason)
