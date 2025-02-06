import datetime
import json
import logging
import sys

import flask
from cryptography.fernet import Fernet
from flask import redirect, request
from slack_bolt import App
from waitress import serve


def purge_expired():
    global auth_list
    popping = []
    for auth_id in auth_list:
        if (
            auth_list[auth_id]["from"] + config["auth_server"]["expiry"]
            > datetime.datetime.now().timestamp()
        ):
            popping.append(auth_id)
    for auth_id in popping:
        auth_list.pop(auth_id)
    logger.debug(
        f"Got {len(auth_list)} auths from file and purged {len(popping)} expired auths"
    )


def redirect_page(link):
    with open("./web/auth_success.html", "r") as f:
        return f.read().replace("REDIRECT_URL", link)


with open("config.json", "r") as f:
    config: dict = json.load(f)

# Set up logging
logger = logging.getLogger("auth server")
ch = logging.StreamHandler()

# Set up the format for the handler
formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
ch.setFormatter(formatter)

ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

if "-v" in sys.argv:
    # Set the log level to DEBUG
    logger.setLevel(logging.DEBUG)
    logger.info("Log level set to DEBUG")
else:
    # Set the log level to INFO
    logger.setLevel(logging.INFO)
    logger.info("Log level set to INFO")

app = flask.Flask(__name__)


@app.route("/", methods=["GET"])  # type: ignore
def index():
    with open("./web/index.html", "r") as f:
        return f.read()


@app.route("/api/v1/authList", methods=["GET"])  # type: ignore
def return_auth_list():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ")[1]
    else:
        return flask.jsonify({"error": "No token provided"}), 401

    if token != config["auth_server"]["query_token"]:
        return flask.jsonify({"error": "Invalid token"}), 403

    # purge expired auths
    purge_expired()

    return flask.jsonify(auth_list), 200


@app.route("/api/v1/authRequest/<en_request>", methods=["GET"])  # type: ignore
def request_auth(en_request):
    auth_request = en_request.encode()

    global auth_list

    # Decrypt the request and convert it from json to a dict
    request_d = json.loads(crypt.decrypt(auth_request).decode())

    # Check if the request is valid
    if not request_d["id"] or not request_d["name"] or not request_d["from"]:
        logger.debug("Parameter missing from request")
        return flask.jsonify({"error": "auth_request is malformed"}), 400

    # Check if the requested ID is already on the list
    if request_d["id"] in auth_list:
        auth_list[request_d["id"]]["from"] = request_d["from"]
        auth_list[request_d["id"]]["name"] = request_d["name"]

    else:
        auth_list[request_d["id"]] = request_d

    # Save the auth list to file
    with open("temp_auths.json", "w") as f:
        json.dump(auth_list, f)

    return redirect_page(link=deep_link)


if __name__ == "__main__":
    logger.info("Auth server starting")

    # Set up decryption
    crypt = Fernet(config["auth_server"]["request_key"].encode())

    # Check if we have an existing auth list
    try:
        with open("temp_auths.json", "r") as f:
            auth_list: dict = json.load(f)
    except FileNotFoundError:
        auth_list = {}

    purge_expired()

    # Get the IDs associated with our Slack credentials for creating deep links

    # Set up the slack app
    slack_app = App(token=config["slack"]["bot_token"])

    # Get our own bot info to retrieve the bot ID and team ID
    slack_bot_info = slack_app.client.auth_test()
    team_id = slack_bot_info["team_id"]
    bot_id = slack_bot_info["bot_id"]

    # Use the bot ID to get the app ID
    slack_bot_info = slack_app.client.bots_info(bot=bot_id)
    app_id = slack_bot_info["bot"]["app_id"]

    deep_link = f"slack://app?team={team_id}&id={app_id}&tab=home"

    serve(app, host=config["auth_server"]["host"], port=config["auth_server"]["port"])
