import json
from pprint import pprint
from typing import Literal, Any
import requests
import os
import sys
from rsc import util,validators,formatters,fileOperators,slackUtils

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
def handle_message_events(body, logger, event): # type: ignore
    user: str = event["user"]
    
    # Discard message types we don't care about
    if event.get("subtype","") != "file_share":
        print("Wrong message type, ignoring")
        return
    
    # Check if the user is in our list of authed users
    if user not in authed_slack_users:
        slackUtils.send(event=event, message=f'This service may only be used by users that have registered with TidyHQ.\nIf you hold, or have previously held, a membership with us then we were unable to automatically link your Slack and TidyHQ accounts. Please contact a committee member for assistance.\nIf you are not registered with TidyHQ you can sign up <{config["tidyhq"]["signup_url"]}|here>.')
        return
    
    # Check if the Member Work folder exists
    if not os.path.exists(f'{config["download"]["root_directory"]}/{formatters.get_folder_name(contact_object=authed_slack_users[user])}'):
        slackUtils.send(event=event, message=f'It looks like you don\'t have a folder in the Member Work directory. Or if you do it\'s not named `{formatters.get_folder_name(contact_object=authed_slack_users[user])}`. I\'ve created it for you.')
    
    # Check if the butler folder exists
    if not os.path.exists(f'{config["download"]["root_directory"]}/{formatters.get_folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'):
        slackUtils.send(event=event, message=f'It looks like you haven\'t used me before. When I save files for you I put them in a folder called `{config["download"]["folder_name"]}` inside your folder in the Member Work directory. I\'ve created it for you.')
    
    # Create the folder if it doesn't exist
    folder = f'{config["download"]["root_directory"]}/{formatters.get_folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    for file in event["files"]:
        # Check if the file is a duplicate
        if os.path.exists(f'{folder}/{file["name"]}'):
            slackUtils.send(event=event, message=f'`{file["name"]}` has been ignored as it already exists in your butler folder. You can find it here: `{folder}/{file["name"]}`. To replace it please delete/move the existing file and upload the new version.')
        
        # Check if the file is too large
        if not validators.check_size(file_object=file):
            slackUtils.send(event=event, message=f'`{file["name"]}` is {file["size"]} bytes, which is larger than the limit of {config["download"]["max_file_size"]} bytes. It has been ignored.')
            continue
        
        # Check if the folder is full
        if not fileOperators.check_folder_eligibility(formatters.get_folder_name(contact_object=authed_slack_users[user])): # type: ignore
            slackUtils.send(event=event, message=f'`{file["name"]}` has been ignored as your butler folder is full. You may only have {config["download"]["max_folder_files"]} files in your folder, and the total size of your butler folder may not exceed {config["download"]["max_folder_size"]} bytes. To remedy this please delete/move some files from the {config["download"]["folder_name"]} folder to somewhere else in your member directory.')
            # Since the folder is full we can stop processing files
            return
        
        # Download the file
        file_data = requests.get(file["url_private"], headers={"Authorization": f'Bearer {config["slack"]["bot_token"]}'})
        
        # Save the file
        
        with open(f'{folder}/{file["name"]}', "wb") as f:
            f.write(file_data.content)
        
        slackUtils.send(event=event, message=f'`{file["name"]}` has been saved to your butler folder. You can find it here: `{folder}/{file["name"]}`')
    
# Get all linked users from TidyHQ

print("Pulling TidyHQ contacts...")

contacts: list[dict[str,Any]] = requests.get(
    "https://api.tidyhq.com/v1/contacts/",
    params={"access_token": config["tidyhq"]["token"]},
).json()

print(f"Received {len(contacts)} contacts")

authed_slack_users = {}
for contact in contacts:
    for field in contact["custom_fields"]:
        if field["id"] == config["tidyhq"]["ids"]["slack"]:
            authed_slack_users[field["value"]] = contact

print(f'Found {len(authed_slack_users)} TidyHQ contacts with associated Slack accounts')

# Get our user ID
info = app.client.auth_test()
print(f'Connected as @{info["user"]} to {info["team"]}')

if __name__ == "__main__":
    handler = SocketModeHandler(app, config["slack"]["app_token"])
    handler.start()
