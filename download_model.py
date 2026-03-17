"""
Download the trained CNN model from the digitrec repository
"""
import os
import requests
from urllib.parse import urlparse

def download_file(url, local_path):
    """Download a file from URL to local path"""
    print(f"Downloading {url}...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Downloaded to {local_path}")
    print(f"File size: {os.path.getsize(local_path) / (1024*1024):.1f} MB")

def main():
    # URL to the trained model in the digitrec branch
    model_url = "https://github.com/varshitha99999/Scan2Score/raw/digitrec/digit_recognizer.keras"
    local_path = "models/digit_recognizer.keras"
    
    try:
        download_file(model_url, local_path)
        print("\n🎉 Model downloaded successfully!")
        print("You can now use the roll number detection feature.")
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print("\nAlternative: Manually download the model from:")
        print("https://github.com/varshitha99999/Scan2Score/blob/digitrec/digit_recognizer.keras")
        print("And save it as 'models/digit_recognizer.keras'")

if __name__ == "__main__":
    main()