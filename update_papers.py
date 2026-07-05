import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("papers.json")

QUERIES = [
    '("greenhouse gas" OR methane OR "carbon dioxide" OR "nitrous oxide" OR CH4 OR CO2 OR N2O) AND (river OR lake OR reservoir OR wetland OR pond OR stream OR riparian OR littoral OR shoreline OR "drawdown zone" OR sediment)',
    '("stable isotope" OR "methane isotope" OR "clumped isotope" OR "methane clumped isotope" OR "δ13C" OR "δD") AND (methane OR CH4 OR "carbon dioxide" OR CO2) AND (lake OR river OR reservoir OR wetland OR sediment OR riparian)',
    '("greenhouse gas flux" OR "methane ebullition" OR "diffusive flux" OR "floating chamber") AND (lake OR river OR reservoir OR wetland OR pond OR riparian)',
]

FIELDS = ",".join([
    "paperId",
    "title",
    "abstract",
    "year",
    "publicationDate",
    "authors",
    "venue",
    "citationCount",
    "referenceCount",
    "externalIds",
    "url",
    "openAccessPdf"
])

TAG_RULES = [
    ("CO2", ["co2", "carbon dioxide"]),
    ("CH4", ["ch4", "methane"]),
    ("N2O", ["n2o", "nitrous oxide"]),
    ("河流", ["river", "stream"]),
    ("湖泊", ["lake"]),
    ("水库", ["reservoir"]),
    ("湿地", ["wetland", "marsh", "swamp"]),
    ("河口", ["estuary", "estuarine"]),
    ("池塘", ["pond"]),
    ("沟渠", ["ditch"]),
    ("岸带", ["riparian", "littoral", "shoreline", "aquatic-terrestrial"]),
    ("消落带", ["drawdown zone", "water-level fluctuation"]),
    ("沉积物", ["sediment"]),
    ("扩散通量", ["diffusive flux", "diffusion"]),
    ("冒泡释放", ["ebullition", "bubbling"]),
    ("浮箱法", ["floating chamber", "chamber"]),
    ("碳氮循环", ["carbon", "nitrogen"]),
    ("微生物过程", ["microbial", "microbiome", "methanogen", "methanotroph"]),
    ("稳定同位素", ["stable isotope"]),
    ("甲烷同位素", ["methane isotope", "δ13c-ch4", "δd-ch4"]),
    ("甲烷团簇同位素", ["clumped isotope", "methane clumped isotope"]),
    ("同位素示踪", ["isotope tracing", "isotopic constraint", "isotopic evidence"]),
    ("甲烷来源解析", ["methane source", "methane origin", "source apportionment"]),
    ("δ13C-CH4", ["δ13c-ch4", "13c-ch4"]),
    ("δD-CH4", ["δd-ch4", "d-ch4"]),
    ("δ13C-CO2", ["δ13c-co2", "13c-co2"]),
    ("clumped isotope", ["clumped isotope"]),
    ("methane clumped isotope", ["methane clumped isotope"]),
    ("stable isotope", ["stable isotope"]),
    ("城市水体", ["urban river", "urban lake", "urban water"]),
]

def request_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "greenhouse-gas-paper-tracker/1.0"
        }
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))

def search_semantic_scholar(query, limit=100):
    params = urllib.parse.urlencode({
        "query": query,
        "limit": limit,
        "fields": FIELDS
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    data = request_json(url)
    return data.get("data", [])

def build_tags(paper):
    text = " ".join([
        paper.get("title") or "",
        paper.get("abstract") or "",
        paper.get("venue") or ""
    ]).lower()

    tags = []
    for tag, keywords in TAG_RULES:
        if any(keyword.lower() in text for keyword in keywords):
            tags.append(tag)

    if "水体" not in tags and any(tag in tags for tag in ["河流", "湖泊", "水库", "湿地", "河口", "池塘", "沟渠"]):
        tags.insert(0, "水体")

    return tags[:12]

def normalize_paper(paper):
    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI")
    authors = paper.get("authors") or []
    open_pdf = paper.get("openAccessPdf") or {}

    return {
        "id": paper.get("paperId"),
        "title": paper.get("title") or "",
        "abstract": paper.get("abstract") or "",
        "authors": ", ".join(author.get("name", "") for author in authors[:8] if author.get("name")),
        "journal": paper.get("venue") or "",
        "year": paper.get("year"),
        "publicationDate": paper.get("publicationDate") or paper.get("year") or "",
        "citations": paper.get("citationCount") or 0,
        "references": paper.get("referenceCount") or 0,
        "source": "Semantic Scholar",
        "doi": doi or "",
        "paperUrl": paper.get("url") or "",
        "pdfUrl": open_pdf.get("url") or "",
        "tags": build_tags(paper),
        "updatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }

def sort_key(paper):
    date_value = str(paper.get("publicationDate") or paper.get("year") or "")
    return date_value

def main():
    collected = {}

    for query in QUERIES:
        print(f"Searching: {query}")
        try:
            results = search_semantic_scholar(query)
        except Exception as error:
            print(f"Search failed: {error}")
            continue

        for item in results:
            normalized = normalize_paper(item)
            key = normalized.get("doi") or normalized.get("id") or normalized.get("title")
            if key and normalized.get("title"):
                collected[key] = normalized

        time.sleep(3)

    papers = list(collected.values())
    papers.sort(key=sort_key, reverse=True)
    papers = papers[:300]

    OUTPUT_FILE.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Saved {len(papers)} papers to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
