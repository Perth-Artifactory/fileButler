import hashlib
import requests


def is_virus(content=None, hash=None, config=None):
    if not config:  # type: ignore
        raise Exception("Global variable config not created")

    if not content and not hash:
        raise Exception("Must provide either content or hash")

    if content and hash:
        raise Exception("Must provide either content or hash, not both")

    file_hash = None

    if content:
        # Get the file hash
        file_hash = hashlib.sha256(content).hexdigest()

    elif hash:
        file_hash = hash

    if not file_hash:
        raise Exception("File hash could not be calculated")

    # Query VirusTotal
    headers = headers = {
        "accept": "application/json",
        "x-apikey": config["virustotal"]["api_key"],
    }

    response = requests.get(
        f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers
    ).json()

    if response.get("error", None):
        if response["error"]["code"] == "NotFoundError":
            return False

    if response["data"]["attributes"]["reputation"] < 0:
        return response["data"]["attributes"]["meaningful_name"]

    return False
