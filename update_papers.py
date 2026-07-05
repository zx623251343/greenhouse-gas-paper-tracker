import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("papers.json")
MAX_PAPERS = 300
FROM_YEAR = 2018

SEARCH_TERMS = [
    "greenhouse gas methane lake",
    "greenhouse gas methane river",
    "greenhouse gas methane reservoir",
    "greenhouse gas methane wetland",
    "greenhouse gas carbon dioxide lake",
    "greenhouse gas carbon dioxide river",
    "greenhouse gas nitrous oxide wetland",
    "methane emission lake",
    "methane emission river",
    "methane emission reservoir",
    "methane emission wetland",
    "carbon dioxide emission lake",
    "carbon dioxide emission river",
    "nitrous oxide emission wetland",
    "methane ebullition lake sediment",
    "methane ebullition reservoir sediment",
    "diffusive greenhouse gas flux river",
    "diffusive methane flux lake",
    "floating chamber greenhouse gas wetland",
    "floating chamber methane lake",
    "riparian greenhouse gas methane",
    "riparian nitrous oxide emission",
    "littoral zone methane emission",
    "drawdown zone methane reservoir",
    "aquatic terrestrial interface greenhouse gas",
    "sediment methane production lake",
    "sediment methane oxidation wetland",
    "stable isotope methane lake sediment",
    "stable isotope methane wetland sediment",
    "methane isotope lake sediment",
    "methane isotope wetland",
    "methane clumped isotope sediment",
    "clumped isotope methane",
    "carbon isotope methane aquatic sediment",
    "stable isotopes carbon dioxide methane river",
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
    "openAccessPdf",
])

TAG_RULES = [
    ("CO2", ["co2", "carbon dioxide"]),
    ("CH4", ["ch4", "methane"]),
    ("N2O", ["n2o", "nitrous oxide"]),
    ("河流", ["river", "stream"]),
    ("湖泊", ["lake"]),
    ("水库", ["reservoir"]),
    ("湿地", ["wetland", "marsh", "swamp", "peatland"]),
    ("河口", ["estuary", "estuarine"]),
    ("池塘", ["pond"]),
    ("沟渠", ["ditch"]),
    ("岸带", ["riparian", "littoral", "shoreline", "aquatic terrestrial", "aquatic-terrestrial"]),
    ("消落带", ["drawdown zone", "water level fluctuation", "water-level fluctuation"]),
    ("沉积物", ["sediment"]),
    ("扩散通量", ["diffusive flux", "diffusion", "gas transfer"]),
    ("冒泡释放", ["ebullition", "bubble", "bubbling"]),
    ("浮箱法", ["floating chamber", "chamber"]),
    ("碳氮循环", ["carbon", "nitrogen", "biogeochemical"]),
    ("微生物过程", ["microbial", "microbiome", "methanogen", "methanotroph"]),
    ("稳定同位素", ["stable isotope", "stable isotopes"]),
    ("甲烷同位素", ["methane isotope", "carbon isotope methane", "hydrogen isotope methane"]),
    ("甲烷团簇同位素", ["clumped isotope", "methane clumped isotope"]),
    ("同位素示踪", ["isotope tracing", "isotopic", "isotope"]),
    ("甲烷来源解析", ["methane source", "methane origin", "source apportionment"]),
    ("δ13C-CH4", ["δ13c-ch4", "13c-ch4", "carbon isotope methane"]),
    ("δD-CH4", ["δd-ch4", "d-ch4", "hydrogen isotope methane"]),
    ("δ13C-CO2", ["δ13c-co2", "13c-co2", "carbon isotope carbon dioxide"]),
    ("clumped isotope", ["clumped isotope"]),
    ("methane clumped isotope", ["methane clumped isotope"]),
    ("stable isotope", ["stable isotope"]),
    ("城市水体", ["urban river", "urban lake", "urban water"]),
]

POSITIVE_KEYWORDS = [
    "greenhouse gas", "methane", "ch4", "carbon dioxide", "co2", "nitrous oxide", "n2o",
    "emission", "emissions", "flux", "fluxes", "ebullition", "diffusive flux", "floating chamber",
    "lake", "river", "reservoir", "wetland", "pond", "stream", "sediment", "estuary",
    "riparian", "littoral", "shoreline", "drawdown zone", "aquatic-terrestrial",
    "stable isotope", "isotope", "isotopic", "clumped isotope", "methane isotope",
]

CORE_GAS_KEYWORDS = [
    "greenhouse gas", "methane", "ch4", "carbon dioxide", "co2", "nitrous oxide", "n2o",
]

CORE_ENV_KEYWORDS = [
    "lake", "river", "reservoir", "wetland", "pond", "stream", "sediment",
    "riparian", "littoral", "shoreline", "drawdown zone", "aquatic", "estuary",
]

NEGATIVE_KEYWORDS = [
    "combustion", "engine", "fuel cell", "coal mine", "natural gas pipeline",
    "biogas reactor", "anaerobic digester", "landfill", "wastewater treatment plant",
    "medical", "clinical", "patient", "tumor", "cancer", "battery", "photocatalyst",
    "cement", "steel", "building material", "coal-fired",
]


def request_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "greenhouse-gas-paper-tracker/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_doi(doi):
    if not doi:
        return ""
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi.strip().lower()


def paper_key(paper):
    doi = normalize_doi(paper.get("doi"))
    if doi:
        return f"doi:{doi}"

    title = normalize_text(paper.get("title")).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    return f"title:{title}" if title else ""


def build_tags(title, abstract, journal):
    text = " ".join([title or "", abstract or "", journal or ""]).lower()

    tags = []
    for tag, keywords in TAG_RULES:
        if any(keyword.lower() in text for keyword in keywords):
            tags.append(tag)

    water_tags = ["河流", "湖泊", "水库", "湿地", "河口", "池塘", "沟渠"]
    if "水体" not in tags and any(tag in tags for tag in water_tags):
        tags.insert(0, "水体")

    if not tags:
        tags = ["水体"]

    return tags[:14]


def relevance_score(paper):
    text = " ".join([
        paper.get("title") or "",
        paper.get("abstract") or "",
        paper.get("journal") or "",
        " ".join(paper.get("tags") or []),
    ]).lower()

    score = 0

    for keyword in POSITIVE_KEYWORDS:
        if keyword in text:
            score += 2

    if any(keyword in text for keyword in CORE_GAS_KEYWORDS):
        score += 8

    if any(keyword in text for keyword in CORE_ENV_KEYWORDS):
        score += 8

    if "isotope" in text or "isotopic" in text or "clumped isotope" in text:
        score += 6

    if "flux" in text or "emission" in text or "ebullition" in text:
        score += 5

    for keyword in NEGATIVE_KEYWORDS:
        if keyword in text:
            score -= 10

    year = paper.get("year")
    if isinstance(year, int) and year >= 2020:
        score += 3

    if paper.get("doi"):
        score += 2

    return score


def search_semantic_scholar(term, limit=100):
    params = urllib.parse.urlencode({
        "query": term,
        "limit": limit,
        "fields": FIELDS,
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    data = request_json(url)
    return data.get("data", [])


def normalize_paper(item):
    external_ids = item.get("externalIds") or {}
    doi = normalize_doi(external_ids.get("DOI"))
    authors = item.get("authors") or []
    open_pdf = item.get("openAccessPdf") or {}

    title = normalize_text(item.get("title"))
    abstract = normalize_text(item.get("abstract"))
    journal = normalize_text(item.get("venue"))

    return {
        "id": item.get("paperId") or "",
        "title": title,
        "abstract": abstract,
        "authors": ", ".join(author.get("name", "") for author in authors[:8] if author.get("name")),
        "journal": journal,
        "year": item.get("year"),
        "publicationDate": item.get("publicationDate") or item.get("year") or "",
        "citations": item.get("citationCount") or 0,
        "references": item.get("referenceCount") or 0,
        "source": "Semantic Scholar",
        "doi": doi,
        "paperUrl": item.get("url") or "",
        "pdfUrl": open_pdf.get("url") or "",
        "tags": build_tags(title, abstract, journal),
        "updatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def sort_key(paper):
    date_value = str(paper.get("publicationDate") or paper.get("year") or "")
    return (date_value, int(paper.get("citations") or 0))


def main():
    collected = {}

    for term in SEARCH_TERMS:
        print(f"Searching Semantic Scholar: {term}")

        try:
            results = search_semantic_scholar(term)
        except Exception as error:
            print(f"Semantic Scholar search failed: {error}")
            time.sleep(8)
            continue

        for item in results:
            paper = normalize_paper(item)
            key = paper_key(paper)

            if key and paper.get("title"):
                collected[key] = paper

        time.sleep(4)

    papers = []

    for paper in collected.values():
        score = relevance_score(paper)
        paper["score"] = score

        year = paper.get("year")
        if isinstance(year, int) and year < FROM_YEAR:
            continue

        if score >= 12:
            papers.append(paper)

    papers.sort(key=sort_key, reverse=True)
    papers = papers[:MAX_PAPERS]

    OUTPUT_FILE.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved {len(papers)} papers to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
