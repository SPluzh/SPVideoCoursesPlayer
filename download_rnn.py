import urllib.request
from pathlib import Path

url = "https://github.com/GregorR/rnnoise-models/raw/master/beguiling-drafter-2018-08-30/bd.rnn"
dest = Path("resources/bd.rnn")
print(f"Downloading to {dest.absolute()}...")
try:
    urllib.request.urlretrieve(url, dest)
    print("Download complete.")
except Exception as e:
    print(f"Error downloading: {e}")
