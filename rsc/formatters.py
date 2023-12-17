from typing import Any, Literal
import requests


def folder_name(
    id: str | Literal[None] = None,
    contact_object: dict[Any, Any] | Literal[None] = None,
    config=None,
    contacts=None,
) -> str | bool:
    if not config or not contacts:
        raise Exception("Must provide config and contacts")

    contact = None  # type: ignore
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
    
    # Remove any characters that aren't allowed in a folder name
    folder_name = "".join(x for x in folder_name if x.isalnum() or x ==" ")
    return folder_name

def clean_filename(filename: str) -> str:
    # Remove any characters that aren't allowed in a filename
    filename = filename.replace("..", ".")
    filename = "".join(x for x in filename if x.isalnum() or x in " .-_")
    return filename


def file_size(num: int | float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < 1024.0:
            return f"{num:.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}B"
