import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings(InsecureRequestWarning)

PARQUET_FILE = 'logos.snappy.parquet'
SAVE_DIR = 'downloaded_logos'
TEST_LIMIT = 50

os.makedirs(SAVE_DIR, exist_ok=True)


def find_logo_url(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')

    for image in soup.find_all('img'):
        image_link = (
            image.get("data-srcset") or
            image.get("data-src") or
            image.get("data-fallback-src") or
            image.get("src")
        )

        if not image_link:
            continue

        alt = image.get("alt", "").lower()
        classes = ' '.join(image.get('class', [])).lower()

        if 'logo' in image_link.lower() or 'logo' in alt or 'logo' in classes:
            # data-srcset may contain multiple candidates: "logo.png 1x, logo.png 2x"
            if ',' in image_link:
                image_link = image_link.split(',')[0].strip().split(' ')[0]
            return urljoin(base_url, image_link)

    return None


def download_fallback_google(domain):
    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Safari/605.1.15'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            safe_name = domain.replace('.', '_')
            filepath = os.path.join(SAVE_DIR, f"{safe_name}.png")
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False


def process_domain(domain):
    urls_to_try = [
        f"https://www.{domain}",
        f"https://{domain}",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
    }

    html_content = None
    current_url = None
    last_error = None

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False, allow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            current_url = response.url
            break
        except Exception as e:
            last_error = e
            continue

    if html_content:
        logo_url = find_logo_url(html_content, current_url)
        if logo_url:
            try:
                img_response = requests.get(logo_url, headers=headers, timeout=10, verify=False)
                if img_response.status_code == 200:
                    ext = logo_url.split('.')[-1][:4].split('?')[0]
                    if ext.lower() not in ['png', 'jpg', 'jpeg', 'ico', 'svg']:
                        ext = 'png'
                    safe_name = domain.replace('.', '_')
                    filepath = os.path.join(SAVE_DIR, f"{safe_name}.{ext}")
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    return ("SUCCESS_SCRAPE", domain)
            except Exception:
                pass

    # Fallback to Google Favicons API if scraping failed or was blocked
    if download_fallback_google(domain):
        return ("SUCCESS_FALLBACK", domain)

    if isinstance(last_error, (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)):
        return ("DOWN", domain)

    return ("FAILED", domain)


if __name__ == '__main__':
    print(f"Loading data from {PARQUET_FILE}...")
    df = pd.read_parquet(PARQUET_FILE, engine='pyarrow')
    #domains = df['domain'].tolist()[:TEST_LIMIT]
    domains = df['domain'].tolist()
    print(f"Starting download for {len(domains)} domains...\n")

    stats = {"SUCCESS_SCRAPE": 0, "SUCCESS_FALLBACK": 0, "FAILED": 0, "DOWN": 0}

    with ThreadPoolExecutor(max_workers=10) as executor:
        for status_type, domain in executor.map(process_domain, domains):
            print(f"[{status_type}] {domain}")
            stats[status_type] += 1

    total_sites = len(domains)
    valid_sites = total_sites - stats["DOWN"]
    total_success = stats["SUCCESS_SCRAPE"] + stats["SUCCESS_FALLBACK"]
    success_rate = (total_success / valid_sites * 100) if valid_sites > 0 else 0

    print("\n" + "=" * 40)
    print(f"Total domains processed : {total_sites}")
    print(f"Unreachable (excluded)  : {stats['DOWN']}")
    print(f"Valid / online          : {valid_sites}")
    print(f"Logos via scraping      : {stats['SUCCESS_SCRAPE']}")
    print(f"Logos via fallback      : {stats['SUCCESS_FALLBACK']}")
    print(f"Failed (valid domains)  : {stats['FAILED']}")
    print(f"Success rate            : {success_rate:.2f}%")
    print("=" * 40)