import requests
import json
import time
import os


def extract_brewery_data(output_dir="data"):
    """
    Extracts all brewery data from the Open Brewery DB API with pagination.
    Saves the raw output as a JSON file.
    """
    base_url = "https://api.openbrewerydb.org/v1/breweries"
    all_breweries = []
    page = 1
    per_page = 200  # Max per the API documentation

    print("Starting data extraction...")

    while True:
        params = {
            "page": page,
            "per_page": per_page
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Catch standard HTTP errors

            data = response.json()

            # If the API returns an empty list, we've exhausted the dataset
            if not data:
                print("Reached the end of the dataset.")
                break

            all_breweries.extend(data)
            print(f"Fetched page {page} ({len(data)} records). Total so far: {len(all_breweries)}")

            page += 1
            time.sleep(0.2)  # Polite throttle between paginated requests

        except requests.exceptions.RequestException as e:
            print(f"Network error on page {page}: {e}")
            break

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Dump raw data to a local landing zone
    output_path = os.path.join(output_dir, "raw_breweries.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_breweries, f, indent=4)

    print(f"Extraction complete! Saved {len(all_breweries)} records to {output_path}")
    return all_breweries


if __name__ == "__main__":
    # Execute the extract step
    raw_data = extract_brewery_data()