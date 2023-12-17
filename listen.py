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


# Update the app home
@app.event("app_home_opened")  # type: ignore
def app_home_opened(event: dict[str, Any], client: WebClient, ack) -> None:
    ack()
    slackUtils.updateHome(user=event["user"], client=client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)  # type: ignore


@app.event("message")
def handle_message_events(body, logger, event):  # type: ignore
    if event["type"] == "message" and not event.get("subtype", None):
        # Strip ts from the event so the message isn't sent in a thread
        event.pop("ts")
        slackUtils.send(
            app=app,
            event=event,
            message=strings.dm,
            dm=True
        )
        return
    
    # Discard message types we don't care about
    if event.get("subtype", "") != "file_share":
        print("Wrong message type, ignoring")
        return

    user: str = event["user"]

    notification_ts = None

    # Check if the user is in our list of authed users
    if user not in authed_slack_users:
        # Let the user know
        slackUtils.send(
            app=app,
            event=event,
            message=strings.not_authed.format(
                signup_url=config["tidyhq"]["signup_url"]
            ),
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

    # Check if the Member Work folder exists
    if not os.path.exists(
        f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user], config=config, contacts=contacts)}'
    ):
        slackUtils.send(
            app=app,
            event=event,
            message=strings.no_root_directory.format(
                folder={
                    formatters.folder_name(
                        contact_object=authed_slack_users[user],
                        config=config,
                        contacts=contacts,
                    )
                }
            ),
        )

    # Check if the butler folder exists
    if not os.path.exists(
        f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user], config=config, contacts=contacts)}/{config["download"]["folder_name"]}'
    ):
        slackUtils.send(
            app=app,
            event=event,
            message=strings.no_butler_directory.format(
                folder=config["download"]["folder_name"]
            ),
        )

    # Create the folder if it doesn't exist
    folder = f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user], config=config, contacts=contacts)}/{config["download"]["folder_name"]}'
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Check if the user is a current member and set the quota multiplier
    if slackUtils.check_unlimited(app=app, user=user, config=config):
        multiplier = 1000
    elif user in current_members:
        multiplier = config["download"]["member_multiplier"]
    else:
        multiplier = 1

    for file in event["files"]:
        filename = formatters.clean_filename(file["name"])

        # Check if the file is a duplicate
        if os.path.exists(f"{folder}/{filename}"):
            slackUtils.send(
                app=app,
                event=event,
                message=strings.duplicate_file.format(folder=folder, file=filename),
            )
            continue

        # Check if the file is too large
        if not validators.check_size(
            file_object=file, config=config, multiplier=multiplier
        ):
            slackUtils.send(
                app=app,
                event=event,
                message=strings.file_too_big.format(
                    file=filename,
                    size=formatters.file_size(file["size"]),
                    max_file_size=formatters.file_size(
                        config["download"]["max_file_size"]
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
                        config["download"]["max_folder_size"] * multiplier
                    ),
                    max_folder_files=config["download"]["max_folder_files"]
                    * multiplier,
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
                        config["download"]["max_folder_size"] * multiplier
                    ),
                    max_folder_files=config["download"]["max_folder_files"]
                    * multiplier,
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

        with open(f"{folder}/{filename}", "wb") as f:
            f.write(file_data.content)

        # Let the user know the file was saved
        slackUtils.send(
            app=app,
            event=event,
            message=strings.file_saved.format(file=filename, folder=folder),
        )

        # Send a message to the notification channel
        ts = slackUtils.send(
            app=app,
            event=event,
            message=strings.file_saved_admin.format(
                file=filename, folder=folder, user=user
            ),
            channel=config["slack"]["notification_channel"],
            ts=notification_ts,
        )
        
        # Update the app home
        slackUtils.updateHome(user=user, client=app.client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)

        if not notification_ts:
            notification_ts = ts


@app.action("purge_folder")
def delete_folder(ack, body, logger):
    ack()
    user = body["user"]["id"]

    # Construct folder path
    folder = f'{config["download"]["root_directory"]}/{formatters.folder_name(contact_object=authed_slack_users[user], config=config, contacts=contacts)}/{config["download"]["folder_name"]}'

    # Delete the folder contents
    if fileOperators.delete_folder_contents(folder=folder):
        slackUtils.send(
            app=app,
            event=body,
            message=strings.delete_success,
            dm=True
        )
        
        # Send a message to the notification channel
        slackUtils.send(
            app=app,
            event=body,
            message=strings.delete_success_admin.format(user=user),
            channel=config["slack"]["notification_channel"],
        )
        
        # Update the app home
        slackUtils.updateHome(user=user, client=app.client, config=config, authed_slack_users=authed_slack_users, contacts=contacts, current_members=current_members)


# Get all linked users from TidyHQ

print("Pulling TidyHQ contacts...")

contacts: list[dict[str, Any]] = requests.get(
    "https://api.tidyhq.com/v1/contacts/",
    params={"access_token": config["tidyhq"]["token"]},
).json()

print(f"Received {len(contacts)} contacts")

authed_slack_users = {}
current_members = {}
for contact in contacts:
    for field in contact["custom_fields"]:
        if field["id"] == config["tidyhq"]["ids"]["slack"]:
            authed_slack_users[field["value"]] = contact
            if contact["status"] != "expired":
                current_members[field["value"]] = contact

print(f"Found {len(authed_slack_users)} TidyHQ contacts with associated Slack accounts")

# Get our user ID
info = app.client.auth_test()
print(f'Connected as @{info["user"]} to {info["team"]}')

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    handler.start()
