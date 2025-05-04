import json
import os
from logo_extraction import process_domain, LOGO_DIR

def load_failed_domains(results_path='data/logo_extraction_results.json'):
    with open(results_path) as f:
        results = json.load(f)
    return [d for d, ok in results.items() if not ok]

def retry_failed_domains(failed_domains):
    results = {}
    for i, domain in enumerate(failed_domains):
        print(f"Retry [{i+1}/{len(failed_domains)}] {domain}", end='... ')
        ok = process_domain(domain)
        print('OK' if ok else 'FAILED')
        results[domain] = ok
    return results

def update_results_json(new_results, results_path='data/logo_extraction_results.json'):
    with open(results_path) as f:
        all_results = json.load(f)
    all_results.update(new_results)
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)

def main():
    failed_domains = load_failed_domains()
    print(f"Found {len(failed_domains)} domains to retry.")
    new_results = retry_failed_domains(failed_domains)
    update_results_json(new_results)
    print("Updated extraction results.")

if __name__ == '__main__':
    main()
