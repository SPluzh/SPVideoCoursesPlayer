import os
from pathlib import Path

path = Path("resources/bin/bd.rnnn")
new_path = Path("resources/bin/bd.rnn")

if path.exists():
    try:
        path.rename(new_path)
        print(f"Renamed {path} to {new_path}")
    except Exception as e:
        print(f"Error renaming: {e}")
else:
    print(f"{path} does not exist")
