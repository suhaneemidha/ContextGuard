import json

def load_session(untrusted_data: str):
    """Parse untrusted session data as JSON rather than executable serialization."""
    return json.loads(untrusted_data)
