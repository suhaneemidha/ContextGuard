from pathlib import Path

DATA_DIR = Path("/srv/app/data")

def read_user_file(filename: str) -> str:
    """Read a file requested by the caller."""
    path = DATA_DIR / filename
    return path.read_text()
