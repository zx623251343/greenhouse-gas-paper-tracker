import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path("papers.json")

SEARCH_TERMS = [
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
    "stable isotopes carbon dioxide methane river"
]

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
    ("甲烷同位素", ["methane isotope", "carbon isotope", "hydrogen isotope"]),
    ("甲烷团簇同位素", ["clumped isotope", "methane clumped isotope"]),
    ("同位素示踪", ["isotope tracing", "isotopic", "isotope"]),
    ("甲烷来源解析", ["methane source", "methane origin", "source apportionment"]),
    ("δ13C-CH4", ["δ13c-ch4", "13c-ch4", "carbon isotope methane"]),
    ("δD-CH4", ["δd-ch4", "d-ch4", "hydrogen isotope methane"]),
    ("δ13C-CO2", ["δ13c-co2", "13c-co2", "carbon isotope carbon dioxide"]),
    ("clumped isotope", ["clumped isotope"]),
    ("methane clumped isotope", ["methane clumped isotope"]),
    ("stable isotope", ["stable isotope"]),
    ("城市水体", ["urban river", "urban lake", "urban water"])
]


def request_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "greenhouse-gas-paper-tracker/1.0"
        }
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def restore_abstract(inverted_index):
    if not inverted_index:
        return ""

    positions = []
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions.append((index, word))

    positions.sort()
    return " ".join(word for _, word in positions)


def search_openalex(term, per_page=50):
    params = urllib.parse.urlencode({
        "search": term,
        "per-page": per_page,
        "filter": "from_publication_date:2018-01-01",
        "sort": "publication_date:desc"
    })
    url = f"https://api.openalex.org/works?{params}"
    data = request_json(url)
    return data.get("results", [])


def get_authors(work):
    authorships = work.get("authorships") or []
    names = []

    for authorship in authorships[:8]:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(name)

    return ", ".join(names)


def get_journal(work):
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("display_name") or ""


def get_paper_url(work):
    primary_location = work.get("primary_location") or {}
    landing_page_url = primary_location.get("landing_page_url")
    return landing_page_url or work.get("id") or ""


def get_pdf_url(work):
    primary_location = work.get("primary_location") or {}
    pdf_url = primary_location.get("pdf_url")
    if pdf_url:
        return pdf_url

    best_oa = work.get("best_oa_location") or {}
    return best_oa.get("pdf_url") or ""


def normalize_doi(doi):
    if not doi:
        return ""

    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi.strip()


def build_tags(work, abstract):
    text = " ".join([
        work.get("display_name") or "",
        abstract or "",
        get_journal(work)
    ]).lower()

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


def normalize_work(work):
    abstract = restore_abstract(work.get("abstract_inverted_index"))
    doi = normalize_doi(work.get("doi"))

    referenced_works = work.get("referenced_works") or []

    return {
        "id": work.get("id") or "",
        "title": work.get("display_name") or "",
        "abstract": abstract,
        "authors": get_authors(work),
        "journal": get_journal(work),
        "year": work.get("publication_year"),
        "publicationDate": work.get("publication_date") or work.get("publication_year") or "",
        "citations": work.get("cited_by_count") or 0,
        "references": len(referenced_works),
        "source": "OpenAlex",
        "doi": doi,
        "paperUrl": get_paper_url(work),
        "pdfUrl": get_pdf_url(work),
        "tags": build_tags(work, abstract),
        "updatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }


def sort_key(paper):
    return str(paper.get("publicationDate") or paper.get("year") or "")


def main():
    collected = {}

    for term in SEARCH_TERMS:
        print(f"Searching OpenAlex: {term}")

        try:
            results = search_openalex(term)
        except Exception as error:
            print(f"Search failed: {error}")
            continue

        for work in results:
            paper = normalize_work(work)
            key = paper.get("doi") or paper.get("id") or paper.get("title")

            if not key or not paper.get("title"):
                continue

            collected[key] = paper

        time.sleep(1)

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
