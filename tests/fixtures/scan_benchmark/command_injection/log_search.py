import subprocess

def search_logs(query: str) -> str:
    """Search application logs for a user-provided query."""
    command = "grep " + query + " /var/log/app.log"
    return subprocess.check_output(command, shell=True, text=True)
