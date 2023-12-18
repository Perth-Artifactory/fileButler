import os
from typing import Literal

from . import formatters


def check_folder_eligibility(contacts, contact: dict, config=None, current_members: dict|Literal[None]=None,authed_slack_users: dict|Literal[None]=None, user: str="", multiplier=0) -> bool:
    
    if not config:
        raise Exception("Must provide config")
    
    if not current_members:
        current_members = {}
    
    if multiplier == 0:
        multiplier = 1
    
        if user in current_members:
            multiplier = config["download"]["member_multiplier"]
    
    folder_name = formatters.folder_name(contact_object=contact, config=config, contacts=contacts)
    
    folder = f'{config["download"]["root_directory"]}/{folder_name}/{config["download"]["folder_name"]}/'
    
    # Check if the folder has reached the maximum number of files
    if len(os.listdir(folder)) >= config["download"]["max_folder_files"] * multiplier:
        return False
    
    # Check if the folder size is over the maximum size
    folder_size = get_current_folder_size(folder)
    if folder_size >= config["download"]["max_folder_size"] * multiplier:
        return False
    return True

def get_current_files(folder=None, user: str="", config={}, contacts=None, authed_slack_users=None):
    if folder:
        dir = folder
    elif user and config and contacts and authed_slack_users:
        dir = f'{config["download"]["root_directory"]}/{formatters.folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users)}/{config["download"]["folder_name"]}/'
    else:
        raise Exception("Must provide either folder or user, config, contacts and authed_slack_users")
    
    files = []
    for file in os.listdir(dir):
        # get the size of each file
        size = os.path.getsize(f'{dir}/{file}')
        
        # get the creation time of each file
        ctime = os.path.getctime(f'{dir}/{file}')
        
        files.append((file, size, ctime))
    return files

def delete_folder_contents(folder):
    try:
        for file in os.listdir(folder):
            os.remove(f'{folder}/{file}')
    except:
        return False
    return True

def get_current_folder_size(folder=None, user: str="", config={}, contacts=None, authed_slack_users=None):
    if folder:
        dir = folder
    elif user and config and contacts and authed_slack_users:
        dir = f'{config["download"]["root_directory"]}/{formatters.folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users)}/{config["download"]["folder_name"]}/'
    else:
        raise Exception("Must provide either folder or user, config, contacts and authed_slack_users")
    
    folder_size = 0
    for file in os.listdir(dir):
        folder_size += os.path.getsize(f'{dir}/{file}')
    return folder_size