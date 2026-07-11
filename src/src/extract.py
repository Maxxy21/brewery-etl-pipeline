import requests
import json
import time
import os


def extract_brewery_data(output_dir="data"):
    """
    Extracts brewery data from the Open Brewery DB API with pagination.
    Streams the raw output directly to an NDJSON file to minimize memory usage.
    """
    base_url = "https://api.openbrewerydb.org/v1/breweries"
    page = 1
    per_page = 200
    total_records = 0

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "raw_breweries.ndjson")

    print("Starting data extraction...")

    # Open the file once and stream data into it line by line
    with open(output_path, 'w', encoding='utf-8') as f:
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }

            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()

                data = response.json()

                if not data:
                    print("Reached the end of the dataset.")
                    break

                # Write each record as a separate JSON string followed by a newline
                for brewery in data:
                    f.write(json.dumps(brewery) + '\n')
                    total_records += 1

                print(f"Fetched and wrote page {page} ({len(data)} records). Total so far: {total_records}")

                page += 1
                time.sleep(0.2)  # Throttle to not overload the server

            except requests.exceptions.RequestException as e:
                print(f"Network error on page {page}: {e}")
                break

    print(f"Extraction complete! Saved {total_records} records to {output_path}")
    return output_path


if __name__ == "__main__":
    file_path = extract_brewery_data()