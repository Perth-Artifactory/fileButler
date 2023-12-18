import json
import logging
import os
import sys
from pprint import pprint
from typing import Any, Literal
import time

import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

from rsc import auth, fileOperators, formatters, slackUtils, strings, util, validators

# Load config
with open("config.json") as config_file:
    config = json.load(config_file)

# Set up logging

if "-v" in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# Connect to Slack
app = App(token=config["slack"]["bot_token"])


# Update the app home in certain circumstances
@app.event("app_home_opened")  # type: ignore
def app_home_opened(event: dict[str, Any], client: WebClient, ack) -> None:
    ack()
    slackUtils.updateHome(user=event["user"], client=client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)  # type: ignore


@app.event("message")
def handle_message_events(body, logger, event, client):  # type: ignore
    if event["type"] == "message" and not event.get("subtype", None):
        # Strip ts from the event so the message isn't sent in a thread
        event.pop("ts")
        slackUtils.send(app=app, event=event, message=strings.dm, dm=True)
        return

    # Discard message types we don't care about
    if event.get("subtype", "") != "file_share":
        logging.debug("Discarding message event of wrong type")
        return

    user: str = event["user"]

    notification_ts = None

    entitlements = util.check_entitlements(
        user=user,
        config=config,
        authed_slack_users=authed_slack_users,
        current_members=current_members,
        contacts=contacts,
        client=client
    )

    # Users with no entitlements are given info on how to get them
    if not entitlements["folder"]:
        slackUtils.send(
            app=app,
            event=event,
            message=strings.not_authed.format(signup_url=config["tidyhq"]["signup_url"])
            + strings.not_authed_msg_addon,
        )
        # Let the notification channel know
        ts = slackUtils.send(
            app=app,
            event=event,
            message=strings.not_authed_admin.format(user=user),
            channel=config["slack"]["notification_channel"],
            ts=notification_ts,
        )
        if not notification_ts:
            notification_ts = ts

        return

    # Check if the butler folder exists
    if not os.path.exists(entitlements["folder"]):
        slackUtils.send(
            app=app,
            event=event,
            message=strings.no_butler_directory.format(
                folder=config["download"]["folder_name"]
            ),
        )

    # Create the folder if it doesn't exist
    if not os.path.exists(entitlements["folder"]):
        os.makedirs(entitlements["folder"])

    for file in event["files"]:
        filename = formatters.clean_filename(file["name"])

        # Check if the file is a duplicate
        if os.path.exists(f"{entitlements["folder"]}/{filename}"):
            slackUtils.send(
                app=app,
                event=event,
                message=strings.duplicate_file.format(folder=entitlements["folder"], file=filename),
            )
            continue

        # Check if the file is too large
        if not validators.check_size(
            file_object=file, config=config, multiplier=entitlements["multiplier"]
        ):
            slackUtils.send(
                app=app,
                event=event,
                message=strings.file_too_big.format(
                    file=filename,
                    size=formatters.file_size(file["size"]),
                    max_file_size=formatters.file_size(
                        num=1000000000
                        if config["download"]["max_file_size"] * entitlements["multiplier"] > 1000000000
                        else config["download"]["max_file_size"] * entitlements["multiplier"]
                    ),
                ),
            )
            continue

        # Check if the folder is full
        if not fileOperators.check_folder_eligibility(contacts=contacts, contact=authed_slack_users[user], config=config, user=user, multiplier=multiplier):  # type: ignore
            slackUtils.send(
                app=app,
                event=event,
                message=strings.over_folder_limit.format(
                    file=filename,
                    max_folder_size=formatters.file_size(
                        config["download"]["max_folder_size"] * entitlements["multiplier"]
                    ),
                    max_folder_files=config["download"]["max_folder_files"]
                    * entitlements["multiplier"],
                    butler_folder=config["download"]["folder_name"],
                ),
            )

            # Let the notification channel know
            ts = slackUtils.send(
                app=app,
                event=event,
                message=strings.over_folder_limit_admin.format(
                    file=filename,
                    max_folder_size=formatters.file_size(
                        config["download"]["max_folder_size"] * entitlements["multiplier"]
                    ),
                    max_folder_files=config["download"]["max_folder_files"]
                    * entitlements["multiplier"],
                    butler_folder=config["download"]["folder_name"],
                    user=user,
                ),
                channel=config["slack"]["notification_channel"],
                ts=notification_ts,
                broadcast=True,
            )

            if not notification_ts:
                notification_ts = ts

            # Since the folder is full we can stop processing files
            return

        # Download the file
        file_data = requests.get(
            file["url_private"],
            headers={"Authorization": f'Bearer {config["slack"]["bot_token"]}'},
        )

        # Check the file with VirusTotal
        virus_check = util.is_virus(content=file_data.content, config=config)

        if virus_check:
            # Explicitly warn the notification channel
            ts = slackUtils.send(
                app=app,
                event=event,
                message=strings.virus_found.format(
                    user=user, file=filename, virus_name=virus_check
                ),
                channel=config["slack"]["notification_channel"],
                ts=notification_ts,
                broadcast=True,
            )

            if not notification_ts:
                notification_ts = ts

            # Let the user know there was a problem
            slackUtils.send(
                app=app,
                event=event,
                message=strings.virus_found,
            )
            # If one of the files is a virus stop processing files
            return

        # Save the file

        with open(f"{entitlements["folder"]}/{filename}", "wb") as f:
            f.write(file_data.content)

        # Let the user know the file was saved
        slackUtils.send(
            app=app,
            event=event,
            message=strings.file_saved.format(file=filename, folder=entitlements["folder"]),
        )

        # Send a message to the notification channel
        ts = slackUtils.send(
            app=app,
            event=event,
            message=strings.file_saved_admin.format(
                file=filename, folder=entitlements["folder"], user=user
            ),
            channel=config["slack"]["notification_channel"],
            ts=notification_ts,
        )

        # Update the app home
        slackUtils.updateHome(
            user=user,
            client=app.client,
            config=config,
            authed_slack_users=authed_slack_users,
            contacts=contacts,
            current_members=current_members,
        )

        if not notification_ts:
            notification_ts = ts


@app.action("purge_folder")
def delete_folder(ack, body, client):
    ack()
    user = body["user"]["id"]

    entitlements = util.check_entitlements(
        user=user,
        config=config,
        authed_slack_users=authed_slack_users,
        current_members=current_members,
        contacts=contacts,
        client=client
    )

    # Delete the folder contents
    if fileOperators.delete_folder_contents(folder=entitlements["folder"]):
        slackUtils.send(app=app, event=body, message=strings.delete_success, dm=True)

        # Send a message to the notification channel
        slackUtils.send(
            app=app,
            event=body,
            message=strings.delete_success_admin.format(user=user),
            channel=config["slack"]["notification_channel"],
        )

        # Update the app home
        slackUtils.updateHome(
            user=user,
            client=app.client,
            config=config,
            authed_slack_users=authed_slack_users,
            contacts=contacts,
            current_members=current_members,
        )


@app.action("refresh_home")
def refresh_home(ack, body, client):
    ack()
    slackUtils.updateHome(user=body["user"]["id"], client=client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)  # type: ignore

@app.action("requesting_auth")
def user_off_requesting_auth(ack, body, logger):
    ack()
    user = body["user"]["id"]
    
    count = 0
    while count < 100 and not auth.check_auth(id=user, config=config):
        time.sleep(0.1)
        count += 1
    # Did the user manage to authenticate in time?
    if auth.check_auth(id=user, config=config):
        slackUtils.updateHome(user=user, client=app.client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)
    else:
        # Update the app home with a refresh button
        slackUtils.updateHome(user=user, client=app.client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members, auth_step=2)


# Test if the auth server is up first before fetching data
while not auth.check_server(config=config):
    logging.warning("Auth server is not up, waiting 5 seconds...")
    time.sleep(5)


# Get all linked users from TidyHQ

logging.info("Pulling TidyHQ contacts...")

contacts: list[dict[str, Any]] = requests.get(
    "https://api.tidyhq.com/v1/contacts/",
    params={"access_token": config["tidyhq"]["token"]},
).json()

logging.debug(f"Received {len(contacts)} contacts")

authed_slack_users = {}
current_members = {}
for contact in contacts:
    for field in contact["custom_fields"]:
        if field["id"] == config["tidyhq"]["ids"]["slack"]:
            authed_slack_users[field["value"]] = contact
            if contact["status"] != "expired":
                current_members[field["value"]] = contact

authed_slack_users.pop("UC6T4U150")
current_members.pop("UC6T4U150")

logging.debug(
    f"Found {len(authed_slack_users)} TidyHQ contacts with associated Slack accounts"
)
logging.debug(f"Found {len(current_members)} current members from associated accounts")

# Get our user ID
info = app.client.auth_test()
logging.debug(f'Connected as @{info["user"]} to {info["team"]}')


if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    handler.start()
