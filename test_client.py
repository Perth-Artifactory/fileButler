import datetime
import json
import time
from pprint import pprint

import requests
from cryptography.fernet import Fernet

with open("config.json", "r") as f:
    config: dict = json.load(f)

# Get a list of current auth requests
print("getting current auths")
r = requests.get(
    f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authList",
    headers={"Authorization": "Bearer " + config["auth_server"]["query_token"]},
)
pprint(r.json())

# Post a new auth request
print("submitting an auth request")
# Construct the request
crypt = Fernet(config["auth_server"]["request_key"].encode())

raw_auth_request = {
    "id": "ABCDE",
    "name": "John Doe",
    "from": datetime.datetime.now().timestamp(),
}

# Convert the request to bytes
auth_request = json.dumps(raw_auth_request).encode()

# Encrypt the request
encrypted_auth_request = crypt.encrypt(auth_request)

# send the request
try:
    r = requests.post(
        f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authRequest/{encrypted_auth_request.decode()}",
    )
    if r.status_code == 200:
        print("Server returned 200 OK")
except requests.exceptions.InvalidSchema as e:
    if "slack://" in e.args[0]:
        print("Server returned slack deep link (expected)")
        print(e.args[0].split(" ")[-1])
    else:
        print("Server returned an invalid schema that was not a slack deep link")
        print(e)

print("Sleeping for 5 seconds")
time.sleep(5)

# Get a list of current auth requests again
print("getting current auths again")
r = requests.get(
    f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authList",
    headers={"Authorization": "Bearer " + config["auth_server"]["query_token"]},
)
pprint(r.json())

# Try to get a list of current auths with an invalid token
print("getting current auths with invalid token")
r = requests.get(
    f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authList",
    headers={
        "Authorization": "Bearer " + config["auth_server"]["query_token"] + "nonsense"
    },
)
pprint(r.json())

# Try to get a list of current auths with no token
print("getting current auths with no token")
r = requests.get(
    f"http://{config['auth_server']['host']}:{config['auth_server']['port']}/api/v1/authList",
)
pprint(r.json())
