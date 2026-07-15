import sys
import json
from pathlib import Path
from typing import Any
import requests
from bs4 import BeautifulSoup
import lxml
import re

# Add project root to sys.path (find the directory containing db_structs.py)
_root = Path(__file__).resolve().parent
while _root.parent != _root:
    if (_root / "db_structs.py").exists():
        if str(_root) not in sys.path:
            sys.path.append(str(_root))
        break
    _root = _root.parent

from db_structs import (
    Medium,
    Circle,
    Event,
    EventGroup,
    Source,
    ReliabilityTypes,
    OriginTypes,
    Location,
)

PATH_EVENT = Path(__file__).parent
PATH_CIRCLES_JSON = PATH_EVENT / "circles.json"
NAME = PATH_EVENT.name


def retrieve_soup_fetch_if_needed(url: str) -> BeautifulSoup:
    """Retrieve BeautifulSoup object for the given URL, fetching the content if necessary."""
    html_path = PATH_EVENT / "raw.html"
    if not html_path.exists():
        print(f"Raw HTML file not found, fetching from {url} ...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(
                f"Failed to retrieve data from {url}, status code: {response.status_code}"
            )
        html_path.write_bytes(response.content)
    with html_path.open("rb") as f:
        return BeautifulSoup(f, "html.parser")


def sanitize_string(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[\s\n\t]+", " ", s)
    return s


def main():
    """Create circles.json"""
    # Ensure stdout/stderr handles UTF-8 properly, especially on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    print(f"Retrieving circles information for {NAME} ...")
    raw_url = "https://ketto.xsrv.jp/html/mimiken/clist.cgi?tvm39"
    
    # Parse the HTML content to extract circle information
    soup = retrieve_soup_fetch_if_needed(raw_url)
    circles = []

    # table: with border=1
    tables = soup.select('table[border="1"]')
    
    for table in tables:
        table_rows = table.select("tr")
        if not table_rows:
            raise Exception("No rows found in the circles table.")

        for row in table_rows:  # Skip header row
                cols = row.select("td")
                if len(cols) < 5:
                    print(f"Skipping row with insufficient columns ({len(cols)}): {row}")
                    continue
                if cols[2].get_text(strip=True) == "サークル名":
                    continue  # Skip header row

                # cols[0,1] skipped
                circle_name = sanitize_string(cols[2].get_text(strip=True))
                circle_pen_name = sanitize_string(cols[3].get_text(strip=True))
                position = sanitize_string(cols[4].get_text(strip=True))

                circle_urls = []
                circle_url_tag = cols[2].select_one("a")
                if circle_url_tag and circle_url_tag.has_attr("href"):
                    circle_urls.append(circle_url_tag["href"])
                url_tags = cols[3].select("a")
                for url_tag in url_tags:
                    if url_tag and url_tag.has_attr("href"):
                        circle_urls.append(url_tag["href"])

                circle = Circle(
                    aliases=[circle_name],
                    pen_names=[circle_pen_name] if circle_pen_name else None,
                    links=[url for url in circle_urls] if circle_urls else None,
                    position=position,
                    # comments=", ".join(description_parts) if description_parts else None,
                )
                circles.append(circle)

    # Save the extracted circle information to a JSON file
    with open(PATH_CIRCLES_JSON, "w", encoding="utf-8") as f:
        json.dump([c.get_json() for c in circles], f, ensure_ascii=False, indent=2)
    print(f"Saved {len(circles)} circles to {PATH_CIRCLES_JSON}")


if __name__ == "__main__":
    main()
