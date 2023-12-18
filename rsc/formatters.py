import logging
import os
from copy import deepcopy as copy
from datetime import datetime
from pprint import pprint
from typing import Any, Literal

import requests

from . import auth, blocks, fileOperators, slackUtils, strings, util

# Set up logging

logger = logging.getLogger("formatters")


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
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if num < 1000.0:
            return f"{num:.1f}{unit}"
        num /= 1000.0
    return f"{num:.1f}B"


def home(
    user, config, authed_slack_users, contacts, client, current_members, auth_step=None
) -> list[dict]:
    entitlements = util.check_entitlements(
        user=user,
        config=config,
        authed_slack_users=authed_slack_users,
        current_members=current_members,
        contacts=contacts,
        client=client,
    )

    # If the folder field is blank the user is not entitled to use this service
    if not entitlements["folder"]:
        block_list = copy(blocks.not_authed)
        block_list[-1]["text"]["text"] = block_list[-1]["text"]["text"].replace(
            "{signup_url}", config["tidyhq"]["signup_url"]
        )
        block_list += blocks.divider
        if auth_step != 2:
            block_list += copy(blocks.request_auth_step_1)
            block_list[-1]["accessory"]["url"] = auth.generate_auth_request_url(
                id=user, config=config, client=client
            )
        else:
            block_list += blocks.request_auth_step_2
        return block_list

    if not os.path.exists(entitlements["folder"]):
        os.makedirs(entitlements["folder"])

    folder_size = fileOperators.get_current_folder_size(
        folder=entitlements["folder"],
    )
    folder_items = fileOperators.get_current_files(
        folder=entitlements["folder"],
    )

    if entitlements["user_class"][0] in ["a", "e", "i", "o", "u"]:
        user_class_prefix = "an"
    else:
        user_class_prefix = "a"

    block_list = []
    block_list += blocks.explainer
    block_list += blocks.divider

    block_list += copy(blocks.quota)
    block_list[-2]["text"]["text"] = strings.quota.format(
        user_class_prefix=user_class_prefix,
        user_class=entitlements["user_class"],
        max_file_size=file_size(
            1000000000
            if config["download"]["max_file_size"] * entitlements["multiplier"]
            > 1000000000
            else config["download"]["max_file_size"] * entitlements["multiplier"]
        ),
        current_folder_size=file_size(folder_size),
        max_folder_size=file_size(
            config["download"]["max_folder_size"] * entitlements["multiplier"]
        ),
        folder_size_bar=createProgressBar(
            current=folder_size,
            total=config["download"]["max_folder_size"] * entitlements["multiplier"],
            segments=7,
        ),
        current_folder_items=len(folder_items),
        max_folder_files=config["download"]["max_folder_files"]
        * entitlements["multiplier"],
        folder_items_bar=createProgressBar(
            current=len(folder_items),
            total=config["download"]["max_folder_files"] * entitlements["multiplier"],
            segments=7,
        ),
    )

    block_list += blocks.divider
    block_list += blocks.current_file_list

    # Get list of files in the user's folder
    lines = []
    for file in folder_items:
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

    block_list += copy(blocks.text)
    block_list[-1]["text"]["text"] = "\n".join(lines)

    block_list += blocks.divider

    block_list += copy(blocks.folder_location)
    block_list[-1]["text"]["text"] = blocks.folder_location[-1]["text"]["text"].format(
        folder=entitlements["folder"]
    )

    block_list += blocks.current_file_delete

    return block_list


def createProgressBar(current: int | float, total: int, segments: int = 7) -> str:
    segments = segments * 4 + 2
    if current == 0:
        filled = 0
    else:
        percent = 100 * float(current) / float(total)
        percentagePerSegment = 100.0 / segments
        if percent < percentagePerSegment:
            filled = 1
        elif 100 - percent < percentagePerSegment:
            filled = segments
        else:
            filled = round(percent / percentagePerSegment)
    s = "g" * filled + "w" * (segments - filled)
    final_s = ""

    # Add the starting cap
    final_s += f":pb-{s[0]}-a:"
    s = s[1:]

    # Fill the middle
    while len(s) > 1:
        final_s += f":pb-{s[:4]}:"
        s = s[4:]

    # Add the ending cap
    final_s += f":pb-{s[0]}-z:"

    return final_s
