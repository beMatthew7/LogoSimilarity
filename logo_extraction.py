import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import mimetypes

LOGO_DIR = 'data/logos'
USER_AGENT = 'Mozilla/5.0 (compatible; LogoSimilarityBot/1.0)'

os.makedirs(LOGO_DIR, exist_ok=True)

def get_homepage(domain):
    for prefix in ['https://', 'http://']:
        url = prefix + domain
        try:
            resp = requests.get(url, timeout=8, headers={'User-Agent': USER_AGENT})
            if resp.status_code < 400:
                return resp.text, url
        except Exception:
            continue
    return None, None

def extract_logo_url(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')

    imgs = soup.find_all('img')
    logo_candidates = []
    for img in imgs:
        attrs = ' '.join([str(img.get(attr, '')) for attr in ['class', 'id', 'src', 'alt']]).lower()
        if 'logo' in attrs:
            logo_candidates.append(img)
    if logo_candidates:
        src = logo_candidates[0].get('src')
        if src:
            return urljoin(base_url, src)

    svgs = soup.find_all('svg')
    for svg in svgs:
        attrs = ' '.join([str(svg.get(attr, '')) for attr in ['class', 'id']]).lower()
        if 'logo' in attrs:
    
            return 'data:image/svg+xml;utf8,' + str(svg)

    for tag in soup.find_all(True):
        attrs = ' '.join([str(tag.get(attr, '')) for attr in ['class', 'id']]).lower()
        if 'logo' in attrs:
            style = tag.get('style', '')
            m = re.search(r'background-image:\s*url\(["\']?(.*?)["\']?\)', style)
            if m:
                bg_url = m.group(1)
                return urljoin(base_url, bg_url)

    icons = soup.find_all('link', rel=re.compile('icon', re.I)) + soup.find_all('link', rel=re.compile('apple-touch-icon', re.I))
    for icon in icons:
        if icon.get('href'):
            return urljoin(base_url, icon['href'])
    return None

def download_image(url, out_path):
    try:

        if url.startswith('data:image/svg+xml'):
            svg_data = url.split(',', 1)[1]
            with open(out_path.replace('.png', '.svg'), 'w', encoding='utf-8') as f:
                f.write(svg_data)
            return True
        resp = requests.get(url, timeout=8, headers={'User-Agent': USER_AGENT})
        if resp.status_code < 400 and resp.content:

            ext = None
            ct = resp.headers.get('Content-Type', '')
            if 'svg' in ct:
                ext = '.svg'
            elif 'png' in ct:
                ext = '.png'
            elif 'jpeg' in ct or 'jpg' in ct:
                ext = '.jpg'
            elif 'ico' in ct:
                ext = '.ico'
            else:
                ext = mimetypes.guess_extension(ct)
            if not ext:
                ext = os.path.splitext(url)[1]
            if not ext or ext == '':
                ext = '.png'
            out_path = os.path.splitext(out_path)[0] + ext

            try:
                img = Image.open(BytesIO(resp.content))
                img.verify()
            except Exception:
      
                if not ext in ['.svg', '.ico']:
                    return False
            with open(out_path, 'wb') as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False

def process_domain(domain):
    html, base_url = get_homepage(domain)
    if not html:
        return False
    logo_url = extract_logo_url(html, base_url)
    if not logo_url:
        return False
    out_path = os.path.join(LOGO_DIR, f"{domain.replace('.', '_')}.png")
    return download_image(logo_url, out_path)

def main():
    import pandas as pd
    df = pd.read_parquet('logos.snappy.parquet')
    domains = df['domain'].tolist()
    results = {}
    for i, domain in enumerate(domains):
        print(f"[{i+1}/{len(domains)}] {domain}", end='... ')
        ok = process_domain(domain)
        print('OK' if ok else 'FAILED')
        results[domain] = ok

    import json
    with open('data/logo_extraction_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
