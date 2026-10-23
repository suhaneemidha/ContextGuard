import subprocess

def search_logs(query: str) -> str:
    """Search logs safely and return an empty string when no matches exist."""
    result = subprocess.run(
        ["grep", "--", query, "/var/log/app.log"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result.stdout
