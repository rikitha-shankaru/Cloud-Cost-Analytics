"""
Seed sample pricing data for the cloud cost analytics dashboard.
This script fetches pricing from all providers and normalizes it.
"""

import json
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fetch_pricing import fetch_all_pricing, normalize_pricing_data


def save_normalized_data(output_path: str = "data/normalized.json"):
    """
    Fetch, normalize, and save pricing data to JSON.
    
    Args:
        output_path: Path to save normalized data
    """
    import os
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Fetch from all providers
    print("Fetching pricing data from all providers...")
    raw_data = fetch_all_pricing()
    
    # Normalize and save
    print("Normalizing pricing data...")
    normalized = normalize_pricing_data(raw_data)
    
    with open(output_path, "w") as f:
        json.dump(normalized, f, indent=2)
    
    print(f"Saved {len(normalized)} normalized pricing SKUs to {output_path}")


if __name__ == "__main__":
    save_normalized_data("data/normalized.json")
    print("Done! Run 'python src/dashboard.py' to start the dashboard.")


