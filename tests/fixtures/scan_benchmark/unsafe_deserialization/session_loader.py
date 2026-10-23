import pickle

def load_session(untrusted_data: bytes):
    """Load session data received from an untrusted client."""
    return pickle.loads(untrusted_data)
