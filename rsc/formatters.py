from typing import Any, Literal
import requests

def get_folder_name(id: str|Literal[None]=None, contact_object: dict[Any,Any]|Literal[None]=None) -> str|bool:
    if not config: # type: ignore
        config = {}
        raise Exception("Global variable config not created")
    
    if not contacts: # type: ignore
        contacts = {}
        raise Exception("Global contacts cache not initialised")
    
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