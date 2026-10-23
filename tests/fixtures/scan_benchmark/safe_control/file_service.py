from pathlib import Path

DATA_DIR = Path("/srv/app/data").resolve()

def read_user_file(filename: str) -> str:
    """Read a file only if its resolved path stays inside the data directory."""
    path = (DATA_DIR / filename).resolve()
    if not path.is_relative_to(DATA_DIR):
        raise ValueError("File path escapes the data directory")
    return path.read_text()
