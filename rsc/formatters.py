from typing import Any, Literal
import requests
from . import blocks, fileOperators, strings, slackUtils
from pprint import pprint
from datetime import datetime
import os
from pprint import pprint
from copy import deepcopy as copy


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


def home(user, config, authed_slack_users, contacts, client, current_members) -> list[dict]:
    # Check if user is allowed to use this service
    if user not in authed_slack_users:
        block_list = copy(blocks.not_authed)
        block_list[-1]["text"]["text"] = block_list[-1]["text"]["text"].replace("{signup_url}", config["tidyhq"]["signup_url"])
        return block_list

    folder = f'{config["download"]["root_directory"]}/{folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users)}/{config["download"]["folder_name"]}/'
    print("folder: " + folder)

    if not os.path.exists(folder):
        os.makedirs(folder)

    folder_size = fileOperators.get_current_folder_size(
        folder=folder,
        config=config,
        contacts=contacts,
        authed_slack_users=authed_slack_users,
    )
    folder_items = fileOperators.get_current_files(
        folder=folder,
        config=config,
        contacts=contacts,
        authed_slack_users=authed_slack_users,
    )

    # Get modifier for member/non-member
    user_class = "casual attendee"
    multiplier = 1
    if user in current_members:
        multiplier = config["download"]["member_multiplier"]
        user_class = "registered user"
    # Since a user can be both a member and in an unlimited group we check the group after since it takes precedence
    if slackUtils.check_unlimited(client=client, user=user, config=config):
        multiplier = 1000
        user_class = "administrator"

    if user_class[0] in "aeiou":
        user_class_prefix = "an"
    else:
        user_class_prefix = "a"

    block_list = []
    block_list += blocks.explainer
    block_list += blocks.divider

    block_list += copy(blocks.quota)
    block_list[-2]["text"]["text"] = strings.quota.format(
        user_class_prefix=user_class_prefix,
        user_class=user_class,
        max_file_size=file_size(1000000000 if config["download"]["max_file_size"] * multiplier > 1000000000 else config["download"]["max_file_size"] * multiplier),
        current_folder_size=file_size(folder_size),
        max_folder_size=file_size(config["download"]["max_folder_size"] * multiplier),
        folder_size_bar=createProgressBar(
            current=folder_size,
            total=config["download"]["max_folder_size"] * multiplier,
            segments=7,
        ),
        current_folder_items=len(folder_items),
        max_folder_files=config["download"]["max_folder_files"] * multiplier,
        folder_items_bar=createProgressBar(
            current=len(folder_items),
            total=config["download"]["max_folder_files"] * multiplier,
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

    block_list += copy(blocks.folder_location)
    block_list[-1]["text"]["text"] = blocks.folder_location[-1]["text"]["text"].format(
        folder=folder
    )

    block_list += blocks.divider

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
