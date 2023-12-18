import json
from cryptography.fernet import Fernet
import logging
import sys
import datetime

import flask
from flask import request
from waitress import serve

def purge_expired():
    global auth_list
    popping = []
    for id in auth_list:
        if auth_list[id]["from"] + config["auth_server"]["expiry"] > datetime.datetime.now().timestamp():
            popping.append
    for id in popping:
        auth_list.pop(id)
    logging.debug(f'Got {len(auth_list)} auths from file and purged {len(popping)} expired auths')

with open("config.json", "r") as f:
    config: dict = json.load(f)

# Set up logging

if "-v" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

app = flask.Flask(__name__)

@app.route("/api/v1/authList", methods=["GET"]) # type: ignore
def return_auth_list():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split(" ")[1]
    else:
        return flask.jsonify({"error": "No token provided"}), 401
    
    if token != config["auth_server"]["query_token"]:
        return flask.jsonify({"error": "Invalid token"}), 403
    
    # purge expired auths
    purge_expired()
    
    return flask.jsonify(auth_list), 200

@app.route("/api/v1/authRequest/", methods=["POST"]) # type: ignore
def request_auth():
    if not request.json:
        logging.debug("Request is not json")
        return flask.jsonify({"error": "Request is not json"}), 400
    authRequest = request.json["authRequest"].encode()
    if not authRequest:
        logging.debug("authRequest param not found")
        return flask.jsonify({"error": "No authRequest found"}), 400
    
    global auth_list
    
    # Decrypt the request and convert it from json to a dict
    request_d = json.loads(crypt.decrypt(authRequest).decode())

    # Check if the request is valid
    if not request_d["id"] or not request_d["name"] or not request_d["from"]:
        logging.debug("Parameter missing from request")
        return flask.jsonify({"error": "authRequest is malformed"}), 400
    
    # Check if the requested ID is already on the list
    if request_d["id"] in auth_list:
        auth_list[request_d["id"]]["from"] = request_d["from"]
        auth_list[request_d["id"]]["name"] = request_d["name"]
        
    else:
        auth_list[request_d["id"]] = request_d
        
    # Save the auth list to file
    with open("temp_auths.json", "w") as f:
        json.dump(auth_list, f)
        
    return flask.jsonify({"message": "OK"}), 200

if __name__ == "__main__":
    # Set up decryption
    crypt = Fernet(config["auth_server"]["request_key"].encode())
    
    # Load existing auth list
    with open("temp_auths.json", "r") as f:
        auth_list: list = json.load(f)
    
    purge_expired()

    serve(app, host=config["auth_server"]["host"], port=config["auth_server"]["port"])