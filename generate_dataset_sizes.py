"""Quick utility: scrape every official ZNO/NMT report PDF linked from
testportal.gov.ua's report pages and write filename + size to
dataset_sizes.csv at the project root (no download needed -- file size
comes from the HTTP Content-Length header).

Source pages (found by browsing testportal.gov.ua/dani-ta-analityka/):
- https://testportal.gov.ua/ofzvit/           ZNO reports 2008-2021 + NMT 2022-2025
- https://testportal.gov.ua/ofitsijni-zvity-nmt/   NMT reports 2022-2026 (adds 2026,
  which isn't mirrored on the ofzvit page yet)

Run from anywhere (stdlib only, no extra installs needed):
    python3 generate_dataset_sizes.py
"""
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SOURCE_PAGES = [
    "https://testportal.gov.ua/ofzvit/",
    "https://testportal.gov.ua/ofitsijni-zvity-nmt/",
]
DOC_EXTENSIONS = (".pdf", ".csv", ".xlsx", ".zip", ".doc", ".docx")
OUT_PATH = Path(__file__).resolve().parent / "dataset_sizes.csv"
USER_AGENT = "Mozilla/5.0 (compatible; dataset-size-scraper/1.0)"


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.hrefs.append(value)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def content_length(url: str) -> int | None:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                length = resp.headers.get("Content-Length")
                if length:
                    return int(length)
        except Exception as e:  # noqa: BLE001 -- best-effort across two methods
            last_error = e
            continue
    print(f"  WARNING: could not get size for {url} ({last_error})")
    return None


def extract_doc_links(page_url: str) -> list[str]:
    html = fetch(page_url).decode("utf-8", errors="replace")
    parser = LinkExtractor()
    parser.feed(html)
    links = []
    for href in parser.hrefs:
        absolute = urljoin(page_url, href)
        if absolute.lower().endswith(DOC_EXTENSIONS):
            links.append(absolute)
    return links


def guess_year(url: str) -> int | None:
    # The filename itself reliably encodes the report's exam year (e.g.
    # "ZVIT_ZNO_2016_Tom_1.pdf" -> 2016). The /wp-content/uploads/<year>/
    # folder is NOT reliable for this -- it's the upload date, and a batch
    # of historical reports (2008-2017) was all uploaded together in 2017,
    # which would misdate every one of them if used as the primary source.
    filename = Path(urlparse(url).path).name
    match = re.search(r"(19|20)\d{2}", filename)
    if match:
        return int(match.group())
    match = re.search(r"/uploads/(\d{4})/", urlparse(url).path)
    return int(match.group(1)) if match else None


def main() -> None:
    print("Collecting document links...")
    all_links = []
    for page in SOURCE_PAGES:
        links = extract_doc_links(page)
        print(f"  {page}: {len(links)} document link(s)")
        all_links.extend(links)

    unique_links = sorted(set(all_links))
    print(f"\n{len(unique_links)} unique documents. Fetching sizes...")

    rows = []
    for url in unique_links:
        filename = Path(urlparse(url).path).name
        year = guess_year(url)
        size_bytes = content_length(url)
        size_mb = round(size_bytes / (1024 * 1024), 1) if size_bytes else None
        rows.append((year, filename, size_mb, url))
        size_str = f"{size_mb} MB" if size_mb is not None else "unknown"
        print(f"  {year}  {filename:<45} {size_str}")

    rows.sort(key=lambda r: (r[0] or 0, r[1]))

    with open(OUT_PATH, "w", newline="") as f:
        f.write("year,filename,size_mb\n")
        for year, filename, size_mb, _url in rows:
            f.write(f"{year},{filename},{size_mb if size_mb is not None else ''}\n")

    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
