"""
IEEE-CIS Fraud Detection dataset download helper.

The dataset is hosted on Kaggle and requires authentication.
This script provides instructions and a minimal helper to acquire
the required files:

  - train_transaction.csv
  - train_identity.csv

Place both files in:
    backend/app/ml/data/

Usage (after configuring Kaggle API credentials):
    python -m app.ml.download_dataset

Or download manually from:
    https://www.kaggle.com/c/ieee-fraud-detection/data
"""
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REQUIRED_FILES = ["train_transaction.csv", "train_identity.csv"]


def check_local_files() -> list:
    """Return list of missing required files."""
    missing = []
    for fname in REQUIRED_FILES:
        if not (DATA_DIR / fname).exists():
            missing.append(fname)
    return missing


def download_via_kaggle():
    """Attempt to download using the Kaggle API."""
    try:
        import kaggle
    except ImportError:
        print("ERROR: kaggle package not installed.")
        print("  pip install kaggle")
        sys.exit(1)

    print("Downloading IEEE-CIS Fraud Detection dataset from Kaggle...")
    kaggle.api.competition_download_files(
        "ieee-fraud-detection",
        path=str(DATA_DIR),
        quiet=False,
    )
    print(f"Download complete. Files saved to {DATA_DIR}")


def main():
    missing = check_local_files()
    if not missing:
        print("All required files are present:")
        for f in REQUIRED_FILES:
            print(f"  ✓ {f}")
        return

    print("Missing required files:")
    for f in missing:
        print(f"  ✗ {f}")
    print()
    print("Options:")
    print("  1. Run this script with Kaggle API configured:")
    print(f"       python -m app.ml.download_dataset --download")
    print("  2. Download manually from:")
    print("       https://www.kaggle.com/c/ieee-fraud-detection/data")
    print(f"     and place files in: {DATA_DIR}")

    if "--download" in sys.argv:
        download_via_kaggle()
        # Unzip if needed
        import zipfile
        zip_path = DATA_DIR / "ieee-fraud-detection.zip"
        if zip_path.exists():
            print("Extracting archive...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(DATA_DIR)
            print("Extraction complete.")


if __name__ == "__main__":
    main()
