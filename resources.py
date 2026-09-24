"""
Where homework resources come from - and why they can be trusted.

Two kinds of resources, both chosen so the model cannot invent them:

1. Book sections: a fixed list written by hand and checked against the
   book's table of contents. The model may only PICK from this list.
2. Web resources: found live with the Tavily Search API, restricted to a
   list of trusted educational sites. Every URL is then opened by our own
   code; only links that actually load are kept.
"""

import os
from datetime import date
from urllib.parse import urlparse

import httpx

# Nielsen & Chuang, "Quantum Computation and Quantum Information",
# 10th anniversary edition (Cambridge University Press, 2010).
# Section numbers and page ranges checked against the table of contents.
NC = "Nielsen & Chuang, Quantum Computation and Quantum Information (10th anniv. ed.)"

BOOK_SECTIONS = {
    "state_vector": [
        {"book": NC, "section": "1.2 Quantum bits", "pages": "13-16",
         "focus": "qubit states, measurement probabilities, the Bloch sphere picture"},
        {"book": NC, "section": "2.1.4 Inner products", "pages": "65-68",
         "focus": "bras, kets and inner products; orthogonality and normalization"},
        {"book": NC, "section": "2.2.7 Phase", "pages": "93",
         "focus": "global phase versus relative phase"},
    ],
    "outer_product": [
        {"book": NC, "section": "2.1.4 Inner products", "pages": "65-68",
         "focus": "the outer product |w⟩⟨v| and the completeness relation"},
        {"book": NC, "section": "2.1.6 Adjoints and Hermitian operators", "pages": "69-71",
         "focus": "adjoints, Hermitian operators and projectors"},
    ],
    "density_matrix": [
        {"book": NC, "section": "2.4 The density operator (intro) and 2.4.1 Ensembles of quantum states",
         "pages": "98-101",
         "focus": "the density operator of a pure state and how it describes measurements"},
    ],
    "mixed_state": [
        {"book": NC, "section": "2.4.1 Ensembles of quantum states", "pages": "99-101",
         "focus": "ensembles of pure states and their density operator"},
        {"book": NC, "section": "2.4.2 General properties of the density operator",
         "pages": "101-105",
         "focus": "trace, positivity, pure versus mixed (tr ρ² test), Bloch vector of a mixed state"},
    ],
}

# Web search only looks at these sites (subdomains included).
TRUSTED_DOMAINS = [
    "wikipedia.org",
    "quantum.cloud.ibm.com", "learning.quantum.ibm.com", "qiskit.org", "ibm.com",
    "pennylane.ai",
    "quantum.country",
    "arxiv.org",
    "ocw.mit.edu", "mit.edu", "caltech.edu", "berkeley.edu", "stanford.edu",
    "libretexts.org",
    "youtube.com",
]

TAVILY_URL = "https://api.tavily.com/search"


def book_options(concept_id: str) -> list[dict]:
    return BOOK_SECTIONS.get(concept_id, [])


def is_trusted(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in TRUSTED_DOMAINS)


def url_works(url: str, timeout: float = 8.0) -> bool:
    """Open the link ourselves: it counts only if the page really loads."""
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout,
                          headers={"User-Agent": "QuantumStudyAgent/1.0 (link check)"}) as client:
            with client.stream("GET", url) as response:
                return response.status_code < 400
    except httpx.HTTPError:
        return False


def tavily_available() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def search_web(query: str, max_results: int = 6) -> list[dict]:
    """Tavily search restricted to TRUSTED_DOMAINS. Returns raw results."""
    response = httpx.post(
        TAVILY_URL,
        headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
        json={"query": query, "search_depth": "basic", "max_results": max_results,
              "include_domains": TRUSTED_DOMAINS},
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def find_web_resources(concept_title: str, weak_point: str | None,
                       keep: int = 3) -> list[dict]:
    """Search, then keep only links that are on a trusted site AND load."""
    if not tavily_available():
        return []
    query = f"{concept_title} {weak_point or ''} quantum computing explanation for beginners"
    checked = []
    for result in search_web(query.strip()):
        url = result.get("url", "")
        if not is_trusted(url) or not url_works(url):
            continue
        checked.append({"title": result.get("title") or url, "url": url,
                        "snippet": (result.get("content") or "")[:300],
                        "checked_on": date.today().isoformat()})
        if len(checked) >= keep:
            break
    return checked
