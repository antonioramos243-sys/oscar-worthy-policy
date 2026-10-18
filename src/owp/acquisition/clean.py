"""Turns a policy page's HTML into the cleaned text a corpus stores.

This is the only place raw markup is discarded, and Q1.8 keeps cleaned text
only, so nothing downstream can recover what is dropped here. Two properties
are therefore worth more than fidelity to the page:

  - Headings and paragraph breaks survive. The script writer has to attribute a
    practice to a section, and a reviewer has to find that section again in the
    published policy (Q2.7).
  - Whitespace is normalized here rather than at hash time, which is what makes
    `content_hash` stable when a page's markup churns without its wording
    changing. Q1.6 takes one snapshot with no version history, so a spurious
    diff would have no cheap way of being recognized as spurious.

selectolax is an optional dependency (the `acquisition` extra), so it is
imported inside the function. That keeps `owp targets` and `owp config` usable
on an install that never fetches anything.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selectolax.lexbor import LexborHTMLParser, LexborNode

#: Boilerplate that is never policy text; removed with its contents.
DROPPED_SELECTORS = (
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "iframe",
    "object",
    "form",
    "button",
    "select",
    "nav",
    "aside",
    "footer",
    '[role="navigation"]',
    '[role="contentinfo"]',
    '[role="search"]',
)

#: Chrome that sometimes carries the document's own title instead, so it is
#: dropped only when it holds no heading of its own.
DROPPED_UNLESS_HEADING = ("header", '[role="banner"]')

#: Where the policy body tends to live, best guess first. Falls back to <body>.
CONTENT_ROOTS = ("main", '[role="main"]', "article")

_HEADINGS = {f"h{level}": level for level in range(1, 7)}
_HEADING_SELECTOR = ", ".join(_HEADINGS)

#: `merge_documents` puts each document under a `##` heading, so a heading from
#: inside a document starts two levels deeper and the merged corpus keeps one
#: consistent hierarchy.
_HEADING_OFFSET = 2

#: Elements that end the current paragraph. `br` is included because plenty of
#: policies separate paragraphs with `<br><br>` and nothing else. Anything not
#: listed here and not inline is treated as a block too - see `_emit_children`.
_BLOCKS = frozenset(
    {
        "address",
        "article",
        "blockquote",
        "br",
        "caption",
        "dd",
        "details",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "header",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)

#: Elements whose text belongs to the paragraph around it. Everything outside
#: this set is walked into rather than flattened, because a policy page's own
#: structure is routinely wrapped in custom elements (`<c-wiz>` on Google's
#: policies, for one) and flattening one of those swallows every heading and
#: paragraph inside it into a single unreadable run of text.
_INLINE = frozenset(
    {
        "a",
        "abbr",
        "b",
        "bdi",
        "bdo",
        "big",
        "cite",
        "code",
        "data",
        "del",
        "dfn",
        "em",
        "font",
        "i",
        "img",
        "ins",
        "kbd",
        "mark",
        "nobr",
        "picture",
        "q",
        "s",
        "samp",
        "small",
        "span",
        "strike",
        "strong",
        "sub",
        "sup",
        "time",
        "tt",
        "u",
        "var",
        "wbr",
    }
)

#: Matches anything that would be lost by flattening an inline element.
_STRUCTURE_SELECTOR = ", ".join(sorted(_BLOCKS | set(_HEADINGS)))

#: Characters that read as nothing but are not whitespace to `str.split`.
_INVISIBLE = str.maketrans({"​": "", "‌": "", "﻿": "", "\xad": ""})


def clean_html(html: str) -> str:
    """Extract the policy text from one page, as headed paragraphs.

    Headings become ATX (`### ...`) and paragraphs are separated by a blank
    line, so the result is readable as Markdown without being Markdown: the
    only structure claimed is what the page itself marked up.
    """
    parser = _parse(html)

    for selector in DROPPED_SELECTORS:
        for node in parser.css(selector):
            node.decompose()
    for selector in DROPPED_UNLESS_HEADING:
        for node in parser.css(selector):
            if node.css_first(_HEADING_SELECTOR) is None:
                node.decompose()

    root = parser.body
    for selector in CONTENT_ROOTS:
        candidate = parser.css_first(selector)
        if candidate is not None:
            root = candidate
            break

    blocks: list[str] = []
    if root is not None:
        _emit_children(root, blocks)
    return "\n\n".join(blocks)


def _parse(html: str) -> LexborHTMLParser:
    try:
        from selectolax.lexbor import LexborHTMLParser
    except ImportError as exc:  # pragma: no cover - depends on how owp was installed
        raise ImportError(
            "Policy fetching needs the acquisition extra: pip install 'owp[acquisition]'"
        ) from exc
    return LexborHTMLParser(html)


def _emit(node: LexborNode, out: list[str]) -> None:
    """Append `node`'s blocks to `out`."""
    tag = node.tag
    if tag in _HEADINGS:
        text = _squash(node.text())
        if text:
            level = min(_HEADINGS[tag] + _HEADING_OFFSET, 6)
            out.append(f"{'#' * level} {text}")
        return

    if tag in ("ul", "ol"):
        # One block per list, so the items stay visibly part of one list
        # instead of reading as a run of unrelated one-line paragraphs.
        items: list[str] = []
        _emit_children(node, items)
        if items:
            out.append("\n".join(items))
        return

    if tag == "li":
        # Bulleted so an enumerated practice still reads as a list of them.
        nested: list[str] = []
        _emit_children(node, nested)
        if nested and not nested[0].startswith("#"):
            nested[0] = f"- {nested[0]}"
        out.extend(nested)
        return

    _emit_children(node, out)


def _emit_children(node: LexborNode, out: list[str]) -> None:
    """Walk `node`'s children, buffering inline runs and recursing into blocks."""
    inline: list[str] = []
    for child in node.iter(include_text=True):
        if child.tag == "-text":
            inline.append(child.text(deep=False) or "")
        elif _is_inline(child):
            inline.append(child.text() or "")
        else:
            _flush(inline, out)
            _emit(child, out)
    _flush(inline, out)


def _is_inline(node: LexborNode) -> bool:
    """Whether `node` can be flattened into the paragraph being buffered.

    An inline tag that happens to wrap headings or paragraphs cannot: the page
    is using it as a container, and flattening it would lose that structure.
    """
    return node.tag in _INLINE and node.css_first(_STRUCTURE_SELECTOR) is None


def _flush(inline: list[str], out: list[str]) -> None:
    text = _squash("".join(inline))
    inline.clear()
    if text:
        out.append(text)


def _squash(text: str) -> str:
    """Collapse every run of whitespace to one space.

    `str.split` treats non-breaking and other Unicode spaces as whitespace,
    which is most of what policy pages use; the rest are translated away first.
    """
    return " ".join(text.translate(_INVISIBLE).split())
