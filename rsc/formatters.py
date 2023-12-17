from typing import Any, Literal
import requests
from . import blocks, fileOperators, strings
from pprint import pprint
from datetime import datetime


def folder_name(
    id: str | Literal[None] = None,
    contact_object: dict[Any, Any] | Literal[None] = None,
    config=None,
    contacts=None,
    authed_slack_users={},
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
        if id in authed_slack_users:
            contact: dict = authed_slack_users[id]
        else:
            raise Exception("Contact not found: " + id)
    elif contact_object:
        contact: dict = contact_object

    if not contact or type(contact) != dict:
        raise Exception("Contact not found")

    # Get the folder name from the contact object
    folder_name: str = f'{contact.get("first_name","")} {contact.get("last_name","")}'

    # Remove any characters that aren't allowed in a folder name
    folder_name = "".join(x for x in folder_name if x.isalnum() or x == " ")
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


def home(user, config, authed_slack_users, contacts) -> list[dict]:
    block_list = []
    block_list += blocks.explainer
    block_list += blocks.divider
    block_list += blocks.quota
    block_list += blocks.divider
    block_list += blocks.current_file_list

    # Get list of files in the user's folder
    folder = f'{config["download"]["root_directory"]}/{folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users)}/{config["download"]["folder_name"]}'
    files = fileOperators.get_current_files(folder=folder)
    lines = []
    for file in files:
        lines.append(
            strings.file_item.format(
                file=file[0],
                size=file_size(file[1]),
                epoch=int(file[2]),
                date_str=datetime.fromtimestamp(file[2]).strftime("%d/%m/%Y %H:%M:%S"),
            )
        )
    if not lines:
        lines.append("No files found")

    block_list += blocks.text
    block_list[-1]["text"]["text"] = "\n".join(lines)

    block_list += blocks.divider

    block_list += blocks.current_file_delete

    return block_list
