import pandas as pd
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from extract_favicon import get_best_favicon
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PARQUET_FILE = 'logos.snappy.parquet'
SAVE_DIR = 'downloaded_logos'
TEST_LIMIT = 50

os.makedirs(SAVE_DIR, exist_ok=True)


def process_domain(domain):
    url = f"https://{domain}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    try:
        best_icon = get_best_favicon(url)

        if best_icon:
            ext = best_icon.format if best_icon.format else 'png'

            safe_name = domain.replace('.', '_')
            filepath = os.path.join(SAVE_DIR, f"{safe_name}.{ext}")

            response = requests.get(best_icon.url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return ("SUCCESS", domain)

        return ("FAILED", domain)

    except Exception as e:
        return ("ERROR", domain)


if __name__ == '__main__':
    print(f"Loading data from {PARQUET_FILE}...")
    try:
        df = pd.read_parquet(PARQUET_FILE, engine='pyarrow')
        domains = df['domain'].tolist()[:TEST_LIMIT]
    except Exception as e:
        print(f"Failed to read parquet file: {e}")
        exit()

    print(f"Starting extraction for {len(domains)} domains...\n")

    stats = {"SUCCESS": 0, "FAILED": 0, "ERROR": 0}

    with ThreadPoolExecutor(max_workers=100) as executor:
        for status_type, domain in executor.map(process_domain, domains):
            print(f"[{status_type}] {domain}")
            stats[status_type] += 1

    total = len(domains)
    success_rate = (stats["SUCCESS"] / total) * 100 if total > 0 else 0

    print("\n" + "=" * 40)
    print(f"Total processed : {total}")
    print(f"Success         : {stats['SUCCESS']}")
    print(f"Failed / Error  : {stats['FAILED'] + stats['ERROR']}")
    print(f"Success rate    : {success_rate:.2f}%")
    print("=" * 40)