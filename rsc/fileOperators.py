import os
from . import formatters
from typing import Literal

def check_folder_eligibility(contacts, contact: dict, config=None, current_members: dict|Literal[None]=None, user: str="") -> bool:
    
    if not config:
        raise Exception("Must provide config")
    
    if not current_members:
        current_members = {}
        
    multiplier = 1
    
    if user in current_members:
        multiplier = config["download"]["member_multiplier"]
    
    folder_name = formatters.folder_name(contact_object=contact, config=config, contacts=contacts)
    
    folder = f'{config["download"]["root_directory"]}/{folder_name}/{config["download"]["folder_name"]}/'
    
    # Check if the folder has reached the maximum number of files
    if len(os.listdir(folder)) >= config["download"]["max_folder_files"] * multiplier:
        return False
    
    # Check if the folder size is over the maximum size
    folder_size = 0
    for file in os.listdir(folder):
        folder_size += os.path.getsize(f'{folder}/{file}')
        if folder_size >= config["download"]["max_folder_size"] * multiplier:
            return False
    
    return True