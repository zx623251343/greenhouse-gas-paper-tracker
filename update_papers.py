import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("papers.json")
MAX_PAPERS = 350
FROM_YEAR = 2018
SEMANTIC_DOI_ENRICH_LIMIT = 150

OPENALEX_TERMS = [
    "greenhouse gas methane lake",
    "greenhouse gas methane river",
    "greenhouse gas methane reservoir",
    "greenhouse gas methane wetland",
    "greenhouse gas carbon dioxide lake",
    "greenhouse gas carbon dioxide river",
    "greenhouse gas nitrous oxide wetland",
    "methane ebullition lake sediment",
    "diffusive greenhouse gas flux river",
    "floating chamber greenhouse gas wetland",
    "riparian greenhouse gas methane",
    "littoral zone methane emission",
    "drawdown zone methane reservoir",
    "aquatic terrestrial interface greenhouse gas",
    "stable isotope methane lake sediment",
    "methane isotope wetland sediment",
    "methane clumped isotope sediment",
    "clumped isotope methane",
    "carbon isotope methane aquatic sediment",
    "stable isotopes carbon dioxide methane river",
]

SEMANTIC_SCHOLAR_TERMS = [
    "greenhouse gas methane lake",
    "greenhouse gas methane river",
    "greenhouse gas methane reservoir",
    "greenhouse gas methane wetland",
    "carbon dioxide methane nitrous oxide aquatic",
    "methane ebullition lake sediment",
    "diffusive greenhouse gas flux river",
    "floating chamber greenhouse gas wetland",
    "riparian greenhouse gas methane",
    "littoral zone methane emission",
    "drawdown zone methane reservoir",
    "aquatic terrestrial interface greenhouse gas",
    "stable isotope methane lake sediment",
    "methane isotope wetland sediment",
    "methane clumped isotope sediment",
    "clumped isotope methane",
    "carbon isotope methane aquatic sediment",
]

SEMANTIC_FIELDS = ",".join([
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
    "riparian", "littoral", "shoreline", "drawdown zone", "aquatic terrestrial", "aquatic-terrestrial",
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
    "cement", "steel", "building material", "satellite retrieval only", "coal-fired",
]


def request_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "greenhouse-gas-paper-tracker/1.0"}
    )
    with urllib.request.urlopen(request, timeout=70) as response:
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


def restore_openalex_abstract(inverted_index):
    if not inverted_index:
        return ""

    positions = []
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions.append((index, word))

    positions.sort()
    return " ".join(word for _, word in positions)


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


def search_openalex(term, per_page=60):
    params = urllib.parse.urlencode({
        "search": term,
        "per-page": per_page,
        "filter": f"from_publication_date:{FROM_YEAR}-01-01",
        "sort": "publication_date:desc",
    })
    url = f"https://api.openalex.org/works?{params}"
    data = request_json(url)
    return data.get("results", [])


def openalex_authors(work):
    names = []
    for authorship in (work.get("authorships") or [])[:8]:
        author = authorship.get("author") or {}
        if author.get("display_name"):
            names.append(author["display_name"])
    return ", ".join(names)


def openalex_journal(work):
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("display_name") or ""


def openalex_paper_url(work):
    primary_location = work.get("primary_location") or {}
    return primary_location.get("landing_page_url") or work.get("id") or ""


def openalex_pdf_url(work):
    primary_location = work.get("primary_location") or {}
    if primary_location.get("pdf_url"):
        return primary_location["pdf_url"]

    best_oa = work.get("best_oa_location") or {}
    return best_oa.get("pdf_url") or ""


def normalize_openalex_work(work):
    title = normalize_text(work.get("display_name"))
    abstract = restore_openalex_abstract(work.get("abstract_inverted_index"))
    journal = openalex_journal(work)
    doi = normalize_doi(work.get("doi"))
    referenced_works = work.get("referenced_works") or []

    return {
        "id": work.get("id") or "",
        "title": title,
        "abstract": abstract,
        "authors": openalex_authors(work),
        "journal": journal,
        "year": work.get("publication_year"),
        "publicationDate": work.get("publication_date") or work.get("publication_year") or "",
        "citations": work.get("cited_by_count") or 0,
        "references": len(referenced_works),
        "source": "OpenAlex",
        "doi": doi,
        "paperUrl": openalex_paper_url(work),
        "pdfUrl": openalex_pdf_url(work),
        "tags": build_tags(title, abstract, journal),
        "updatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def search_semantic_scholar(term, limit=80):
    params = urllib.parse.urlencode({
        "query": term,
        "limit": limit,
        "fields": SEMANTIC_FIELDS,
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    data = request_json(url)
    return data.get("data", [])


def fetch_semantic_by_doi(doi):
    doi = normalize_doi(doi)
    if not doi:
        return None

    paper_id = urllib.parse.quote(f"DOI:{doi}", safe="")
    params = urllib.parse.urlencode({"fields": SEMANTIC_FIELDS})
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?{params}"

    try:
        return request_json(url)
    except Exception as error:
        print(f"Semantic Scholar DOI lookup failed for {doi}: {error}")
        return None


def normalize_semantic_paper(item):
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


def merge_paper(existing, incoming):
    if not existing:
        return incoming

    merged = dict(existing)

    for field in ["doi", "journal", "authors", "publicationDate", "year", "paperUrl", "pdfUrl", "abstract"]:
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]

    merged["citations"] = max(int(merged.get("citations") or 0), int(incoming.get("citations") or 0))
    merged["references"] = max(int(merged.get("references") or 0), int(incoming.get("references") or 0))

    tags = []
    for tag in (merged.get("tags") or []) + (incoming.get("tags") or []):
        if tag not in tags:
            tags.append(tag)
    merged["tags"] = tags[:14]

    sources = set(str(merged.get("source") or "").split(" + "))
    sources.add(incoming.get("source") or "")
    merged["source"] = " + ".join(sorted(s for s in sources if s))

    return merged


def sort_key(paper):
    date_value = str(paper.get("publicationDate") or paper.get("year") or "")
    return (date_value, int(paper.get("citations") or 0))


def main():
    collected = {}

    for term in OPENALEX_TERMS:
        print(f"Searching OpenAlex: {term}")
        try:
            results = search_openalex(term)
        except Exception as error:
            print(f"OpenAlex search failed: {error}")
            time.sleep(3)
            continue

        for work in results:
            paper = normalize_openalex_work(work)
            key = paper_key(paper)
            if key and paper.get("title"):
                collected[key] = merge_paper(collected.get(key), paper)

        time.sleep(1)

    for term in SEMANTIC_SCHOLAR_TERMS:
        print(f"Searching Semantic Scholar: {term}")
        try:
            results = search_semantic_scholar(term)
        except Exception as error:
            print(f"Semantic Scholar search failed: {error}")
            time.sleep(5)
            continue

        for item in results:
            paper = normalize_semantic_paper(item)
            key = paper_key(paper)
            if key and paper.get("title"):
                collected[key] = merge_paper(collected.get(key), paper)

        time.sleep(3)

    print("Enriching OpenAlex papers with Semantic Scholar DOI lookup...")

    enriched_count = 0
    for key, paper in list(collected.items()):
        doi = paper.get("doi")
        if not doi:
            continue

        semantic_item = fetch_semantic_by_doi(doi)
        if not semantic_item:
            time.sleep(1)
            continue

        semantic_paper = normalize_semantic_paper(semantic_item)
        collected[key] = merge_paper(collected.get(key), semantic_paper)
        enriched_count += 1
        time.sleep(1)

        if enriched_count >= SEMANTIC_DOI_ENRICH_LIMIT:
            break

    print(f"Enriched {enriched_count} papers with Semantic Scholar")

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

