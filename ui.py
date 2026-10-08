"""
Small layout helpers that stay readable at every window width.

Streamlit columns keep their number at any width, so ten cards in ten
columns squeeze each title to one letter per line when the window is narrow,
and st.metric prints values so large that long names get cut off. These
helpers draw the same information as a CSS grid instead: the browser fits
as many cards per row as there is room for and wraps the rest.
"""

from html import escape
from urllib.parse import quote

import streamlit as st

_CSS = """<style>
.qsa-grid{display:grid;gap:.6rem;margin:.2rem 0 .8rem 0;
  grid-template-columns:repeat(auto-fill,minmax(var(--qsa-min,150px),1fr));}
.qsa-card{border:1px solid rgba(128,128,128,.35);border-radius:.6rem;
  padding:.55rem .75rem;line-height:1.35;overflow-wrap:break-word;}
.qsa-card.qsa-hi{border-color:#3987e5;box-shadow:0 0 0 1px #3987e5 inset;}
.qsa-card.qsa-dim{opacity:.6;}
.qsa-top{font-size:.75rem;opacity:.7;letter-spacing:.02em;}
.qsa-title{font-weight:600;font-size:.95rem;margin:.1rem 0 .25rem 0;}
.qsa-value{font-weight:600;font-size:1.3rem;}
.qsa-sub{font-size:.8rem;opacity:.75;}
.qsa-bar{display:flex;gap:3px;margin:.35rem 0 .15rem 0;}
.qsa-bar span{flex:1;height:6px;border-radius:3px;background:rgba(128,128,128,.3);}
.qsa-bar span.on{background:#3987e5;}
.qsa-links{margin-top:.35rem;font-size:.8rem;display:flex;gap:.6rem;flex-wrap:wrap;}
.qsa-links a{text-decoration:none;border:1px solid rgba(128,128,128,.4);border-radius:1rem;padding:.05rem .55rem;}
</style>"""


def css() -> None:
    """Add the styles once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _bar(done: int, total: int) -> str:
    return ('<div class="qsa-bar">' + "".join(
        f'<span class="{"on" if i < done else ""}"></span>' for i in range(total))
        + "</div>")


def cards(items: list[dict], min_px: int = 150) -> None:
    """A wrapping grid of small cards. Each item may have: top (small caps
    line), title, value (big number), bar=(done, total), sub (grey line),
    highlight (blue frame), dim (faded), links=[(label, url), ...]. All text
    is escaped."""
    parts = []
    for it in items:
        cls = "qsa-card" + (" qsa-hi" if it.get("highlight") else "") + \
              (" qsa-dim" if it.get("dim") else "")
        inner = ""
        if it.get("top"):
            inner += f'<div class="qsa-top">{escape(str(it["top"]))}</div>'
        if it.get("title"):
            inner += f'<div class="qsa-title">{escape(str(it["title"]))}</div>'
        if it.get("value") is not None:
            inner += f'<div class="qsa-value">{escape(str(it["value"]))}</div>'
        if it.get("bar"):
            inner += _bar(*it["bar"])
        if it.get("sub"):
            inner += f'<div class="qsa-sub">{escape(str(it["sub"]))}</div>'
        if it.get("links"):
            inner += '<div class="qsa-links">' + "".join(
                f'<a href="{escape(href, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{escape(label)}</a>'
                for label, href in it["links"]) + "</div>"
        parts.append(f'<div class="{cls}">{inner}</div>')
    st.markdown(f'<div class="qsa-grid" style="--qsa-min:{min_px}px">'
                + "".join(parts) + "</div>", unsafe_allow_html=True)


def stats(items: list[tuple], min_px: int = 120) -> None:
    """Label/value pairs as compact tiles: [(label, value, hint), ...]."""
    tiles = []
    for t in items:
        tiles.append({"top": t[0], "value": t[1], "sub": t[2] if len(t) > 2 else None})
    cards(tiles, min_px)


def share_links(text: str) -> list[tuple]:
    """Ready-made share links (they open the site's own post window with the
    text filled in; nothing is posted until the learner presses Post)."""
    t = quote(text)
    return [("🔗 LinkedIn", f"https://www.linkedin.com/feed/?shareActive=true&text={t}"),
            ("𝕏 Post", f"https://x.com/intent/post?text={t}")]


def explain(points: list[str], tries: list[str] | None = None) -> None:
    """A short "what this means" box under a lab, plus small challenges."""
    with st.container(border=True):
        st.markdown("**💡 What this means**\n\n" + "\n".join(f"- {p}" for p in points))
    if tries:
        with st.expander("🎯 Try this"):
            st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(tries, 1)))
