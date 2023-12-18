import datetime
import json
import time
from pprint import pprint
from typing import Literal

import requests
from cryptography.fernet import Fernet
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

from . import slackUtils


def generate_auth_request_url(id: str, config: dict, name: str="", app=None, client=None):
    if not app and not client:
        raise ValueError("Either app or client must be specified")
    if app:
        slack: WebClient = app.client
    elif client:
        slack: WebClient = client
    else:
        raise ValueError("Could not get slack client")

    if not name:
        # Get display name using slack ID
        name = slackUtils.get_name(id=id, client=slack)

    # Construct the request
    crypt = Fernet(config["auth_server"]["request_key"].encode())

    raw_auth_request = {
        "id": id,
        "name": name,
        "from": datetime.datetime.now().timestamp(),
    }

    # Convert the request to bytes
    auth_request = json.dumps(raw_auth_request).encode()

    # Encrypt the request
    encrypted_auth_request = crypt.encrypt(auth_request)

    # Construct the rest of the URL
    if config["auth_server"].get("proxied_url"):
        domain = config["auth_server"]["proxied_url"]
    else:
        domain = f'http://{config["auth_server"]["host"]}:{config["auth_server"]["port"]}'

    return f"{domain}/api/v1/authRequest/{encrypted_auth_request.decode()}"


def get_auths(config) -> dict:
    r = requests.get(
        f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authList",
        headers={"Authorization": "Bearer " + config["auth_server"]["query_token"]},
    )
    return r.json()


def submit_auth_request(auth_request, config):
    try:
        r = requests.post(
            f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authRequest/{auth_request}",
        )
        if r.status_code != 200:
            raise Exception("Server returned an error")
    except requests.exceptions.InvalidSchema as e:
        if "slack://" in e.args[0]:
            pass
        else:
            raise Exception("Server returned an invalid schema that was not a slack deep link")


    # decode the auth_request
    crypt = Fernet(config["auth_server"]["request_key"].encode())
    decrypted_auth_request = crypt.decrypt(auth_request.encode())
    request_d = json.loads(decrypted_auth_request.decode())

    # check if the auth request is in the list
    auths = get_auths(config)
    if auths.get(request_d["id"], None) != request_d:
        if (
            auths[request_d["name"]] == request_d["name"]
            and auths[request_d["from"]] == request_d["from"]
        ):
            return True
    return False


def check_auth(id, config) -> str | Literal[False]:
    auths = get_auths(config)
    if auths.get(id, None):
        return auths[id]["name"]
    return False

def check_server(config):
    # query the root endpoint
    r = requests.get(url=f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/")
    if r.status_code != 200:
        return False
    return True