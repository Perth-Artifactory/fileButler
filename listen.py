import json
from pprint import pprint
from typing import Literal, Any
import requests
import os
import sys

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient  # for typing
from slack_sdk.web.slack_response import SlackResponse  # for typing

# Load config
with open("config.json") as config_file:
    config = json.load(config_file)
    
# Connect to Slack
app = App(token=config["slack"]["bot_token"])


def check_size(id: str|Literal[None]=None, file_object: dict[Any,Any]|Literal[None]=None) -> int|bool:
    if not id and not file_object:
        raise Exception("Must provide either id or file_object")
    elif id and file_object:
        raise Exception("Must provide either id or file_object, not both")
    if id:
        # Get the file object from the id
        file: SlackResponse = app.client.files_info(file=id) # type: ignore
    # Check the file size against the limit specified in config.json
    elif file_object:
        file: dict = file_object 
    
    size: int = file["size"] # type: ignore
    if size > config["download"]["max_file_size"]:
        return False
    else:
        return int(size)

def get_folder_name(id: str|Literal[None]=None, contact_object: dict[Any,Any]|Literal[None]=None) -> str|bool:
    contact = None # type: ignore
    if not id and not contact_object:
        raise Exception("Must provide either id or contact")
    elif id and contact_object:
        raise Exception("Must provide either id or contact, not both")
    if id:
        # Check if we already have the contact object
        if id in contacts:
            contact: dict = contacts[id]
        else:
            # Get the contact object from the id
            contact: dict = requests.get(
                f"https://api.tidyhq.com/v1/contacts/{id}",
                params={"access_token": config["tidyhq"]["token"]},
            ).json()
    elif contact_object:
        contact: dict = contact_object
    
    if not contact or type(contact) != dict:
        raise Exception("Contact not found")
    
    # Get the folder name from the contact object
    folder_name: str = f'{contact.get("first_name","")} {contact.get("last_name","")}'
    return folder_name

def check_folder_eligibility(folder_name: str) -> bool:
    folder = f'{config["download"]["root_directory"]}/{folder_name}/{config["download"]["folder_name"]}/'
    
    # Check if the folder has reached the maximum number of files
    if len(os.listdir(folder)) >= config["download"]["max_folder_files"]:
        return False
    
    # Check if the folder size is over the maximum size
    folder_size = 0
    for file in os.listdir(folder):
        folder_size += os.path.getsize(f'{folder}/{file}')
        if folder_size >= config["download"]["max_folder_size"]:
            return False
    
    return True

def send(event, message: "str"):
    # Send a threaded message to the user
    app.client.chat_postMessage(
        channel=event["channel"],
        text=message,
        thread_ts=event["ts"],
    )

@app.event("message")
def handle_message_events(body, logger, event): # type: ignore
    user: str = event["user"]
    
    # Discard message types we don't care about
    if event.get("subtype","") != "file_share":
        print("Wrong message type, ignoring")
        return
    
    # Check if the user is in our list of authed users
    if user not in authed_slack_users:
        send(event=event, message=f'This service may only be used by users that have registered with TidyHQ.\nIf you hold, or have previously held, a membership with us then we were unable to automatically link your Slack and TidyHQ accounts. Please contact a committee member for assistance.\nIf you are not registered with TidyHQ you can sign up <{config["tidyhq"]["signup_url"]}|here>.')
        return
    
    # Check if the Member Work folder exists
    if not os.path.exists(f'{config["download"]["root_directory"]}/{get_folder_name(contact_object=authed_slack_users[user])}'):
        send(event=event, message=f'It looks like you don\'t have a folder in the Member Work directory. Or if you do it\'s not named `{get_folder_name(contact_object=authed_slack_users[user])}`. I\'ve created it for you.')
    
    # Check if the butler folder exists
    if not os.path.exists(f'{config["download"]["root_directory"]}/{get_folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'):
        send(event=event, message=f'It looks like you haven\'t used me before. When I save files for you I put them in a folder called `{config["download"]["folder_name"]}` inside your folder in the Member Work directory. I\'ve created it for you.')
    
    # Create the folder if it doesn't exist
    folder = f'{config["download"]["root_directory"]}/{get_folder_name(contact_object=authed_slack_users[user])}/{config["download"]["folder_name"]}'
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    for file in event["files"]:
        # Check if the file is a duplicate
        if os.path.exists(f'{folder}/{file["name"]}'):
            send(event=event, message=f'`{file["name"]}` has been ignored as it already exists in your butler folder. You can find it here: `{folder}/{file["name"]}`. To replace it please delete/move the existing file and upload the new version.')
        
        # Check if the file is too large
        if not check_size(file_object=file):
            send(event=event, message=f'`{file["name"]}` is {file["size"]} bytes, which is larger than the limit of {config["download"]["max_file_size"]} bytes. It has been ignored.')
            continue
        
        # Check if the folder is full
        if not check_folder_eligibility(get_folder_name(contact_object=authed_slack_users[user])): # type: ignore
            send(event=event, message=f'`{file["name"]}` has been ignored as your butler folder is full. You may only have {config["download"]["max_folder_files"]} files in your folder, and the total size of your butler folder may not exceed {config["download"]["max_folder_size"]} bytes. To remedy this please delete/move some files from the {config["download"]["folder_name"]} folder to somewhere else in your member directory.')
            # Since the folder is full we can stop processing files
            return
        
        # Download the file
        file_data = requests.get(file["url_private"], headers={"Authorization": f'Bearer {config["slack"]["bot_token"]}'})
        
        # Save the file
        
        with open(f'{folder}/{file["name"]}', "wb") as f:
            f.write(file_data.content)
        
        send(event=event, message=f'`{file["name"]}` has been saved to your butler folder. You can find it here: `{folder}/{file["name"]}`')
    
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
