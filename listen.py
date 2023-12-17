import json
from pprint import pprint
from typing import Literal, Any
import requests
import os
import sys
from rsc import util, validators, formatters, fileOperators, slackUtils, strings

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

# Load config
with open("config.json") as config_file:
    config = json.load(config_file)

# Connect to Slack
app = App(token=config["slack"]["bot_token"])


@app.event("message")
def handle_message_events(body, logger, event):  # type: ignore
    user: str = event["user"]

    # Discard message types we don't care about
    if event.get("subtype", "") != "file_share":
        print("Wrong message type, ignoring")
        return

    # Check if the user is in our list of authed users
    if user not in authed_slack_users:
        slackUtils.send(
            event=event,
            message=strings.not_authed.format(
                signup_url=config["tidyhq"]["signup_url"]
            ),
        )
        return

    # Check if the Member Work folder exists
    if not os.path.exists(
        f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user])}'
    ):
        slackUtils.send(
            event=event,
            message=strings.no_root_directory.format(
                folder={formatters.folder_name(contact_object=authed_slack_users[user])}
            ),
        )

    # Check if the butler folder exists
    if not os.path.exists(
        f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'
    ):
        slackUtils.send(
            event=event,
            message=strings.no_butler_directory.format(
                folder=config["download"]["folder_name"]
            ),
        )

    # Create the folder if it doesn't exist
    folder = f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'
    if not os.path.exists(folder):
        os.makedirs(folder)

    for file in event["files"]:
        # Check if the file is a duplicate
        if os.path.exists(f'{folder}/{file["name"]}'):
            slackUtils.send(
                event=event,
                message=strings.duplicate_file.format(folder=folder, file=file["name"]),
            )

        # Check if the file is too large
        if not validators.check_size(file_object=file):
            slackUtils.send(
                event=event,
                message=strings.file_too_big.format(
                    file=file["name"],
                    size=formatters.file_size(file["size"]),
                    max_file_size=formatters.file_size(
                        config["download"]["max_file_size"]
                    ),
                ),
            )
            continue

        # Check if the folder is full
        if not fileOperators.check_folder_eligibility(formatters.folder_name(contact_object=authed_slack_users[user])):  # type: ignore
            slackUtils.send(
                event=event,
                message=strings.over_folder_limit.format(
                    file=file["name"],
                    max_folder_size=formatters.file_size(
                        config["download"]["max_folder_size"]
                    ),
                    max_folder_files=config["download"]["max_folder_files"],
                    butler_folder=config["download"]["folder_name"],
                ),
            )
            # Since the folder is full we can stop processing files
            return

        # Download the file
        file_data = requests.get(
            file["url_private"],
            headers={"Authorization": f'Bearer {config["slack"]["bot_token"]}'},
        )

        # Save the file

        with open(f'{folder}/{file["name"]}', "wb") as f:
            f.write(file_data.content)

        slackUtils.send(
            event=event,
            message=strings.file_saved.format(file=file["name"], folder=folder),
        )


# Get all linked users from TidyHQ

print("Pulling TidyHQ contacts...")

contacts: list[dict[str, Any]] = requests.get(
    "https://api.tidyhq.com/v1/contacts/",
    params={"access_token": config["tidyhq"]["token"]},
).json()

print(f"Received {len(contacts)} contacts")

authed_slack_users = {}
for contact in contacts:
    for field in contact["custom_fields"]:
        if field["id"] == config["tidyhq"]["ids"]["slack"]:
            authed_slack_users[field["value"]] = contact

print(f"Found {len(authed_slack_users)} TidyHQ contacts with associated Slack accounts")

# Get our user ID
info = app.client.auth_test()
print(f'Connected as @{info["user"]} to {info["team"]}')

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    handler.start()
