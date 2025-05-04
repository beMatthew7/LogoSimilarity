import os
from PIL import Image
from logo_similarity import list_logo_files, compute_hashes

def get_invalid_logo_files():
    logo_files = list_logo_files('data/logos')
    # Try to hash each; if fails, collect
    invalid_files = []
    for file in logo_files:
        try:
            img = Image.open(file).convert('RGB')
            img.verify()  # Will raise if file is broken
        except Exception as e:
            invalid_files.append((file, str(e)))
    return invalid_files

def summarize_errors(invalid_files):
    from collections import Counter
    error_types = [e for _, e in invalid_files]
    return Counter(error_types)

def main():
    invalid_files = get_invalid_logo_files()
    print(f"Found {len(invalid_files)} invalid logo files.")
    # Print a summary
    summary = summarize_errors(invalid_files)
    print("Summary of errors:")
    for err, count in summary.most_common():
        print(f"{err}: {count}")
    # Optionally, save list for inspection
    with open('output/invalid_logo_files.txt', 'w') as f:
        for file, err in invalid_files:
            f.write(f"{file}\t{err}\n")
    print("Details saved to output/invalid_logo_files.txt")

if __name__ == '__main__':
    main()
