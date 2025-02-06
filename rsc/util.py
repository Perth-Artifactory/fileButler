import hashlib

from . import slackUtils, formatters, fileOperators, formatters, auth
import requests
import logging
from typing import Any

# Set up logging

logger = logging.getLogger("util")


def get_tidy_info(config: dict) -> tuple[dict[Any, Any], dict[Any, Any]]:
    logger.info("Pulling TidyHQ contacts...")

    contacts: list[dict[str, Any]] = requests.get(
        "https://api.tidyhq.com/v1/contacts/",
        params={"access_token": config["tidyhq"]["token"]},
    ).json()

    logger.debug(f"Received {len(contacts)} contacts")

    authed_slack_users = {}
    current_members = {}
    for contact in contacts:
        for field in contact["custom_fields"]:
            if field["id"] == config["tidyhq"]["ids"]["slack"]:
                authed_slack_users[field["value"]] = contact
                if contact["status"] != "expired":
                    current_members[field["value"]] = contact
    logger.debug(
        f"Found {len(authed_slack_users)} TidyHQ contacts with associated Slack accounts"
    )
    logger.debug(
        f"Found {len(current_members)} current members from associated accounts"
    )

    return authed_slack_users, current_members


def check_entitlements(
    user: str,
    config: dict,
    authed_slack_users_local,
    current_members_local,
    contacts,
    app=None,
    client=None,
):
    if app:
        slack = app.client
    elif client:
        slack = client
    else:
        raise Exception("Must provide either app or client")

    # Refresh the info from TidyHQ if the slack user is not known at all
    if user not in authed_slack_users_local:

        global authed_slack_users
        global current_members

        authed_slack_users, current_members = get_tidy_info(config)

        authed_slack_users_local = authed_slack_users
        current_members_local = current_members

    # Entitlements are checked from most to least privileged

    # Check if the user is in an unlimited group
    if (
        slackUtils.check_unlimited(user, config, client=slack)
        and user in authed_slack_users_local
    ):
        multiplier = 1000
        user_class = "administrator"
        folder = f'{config["download"]["root_directory"]}/{formatters.folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users_local)}/{config["download"]["folder_name"]}/'
    # Check if the user holds a current membership
    elif user in current_members_local:
        multiplier = config["download"]["member_multiplier"]
        user_class = "registered user"
        folder = folder = (
            f'{config["download"]["root_directory"]}/{formatters.folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users_local)}/{config["download"]["folder_name"]}/'
        )
    # Check if the user is registered with TidyHQ at all
    elif user in authed_slack_users_local:
        multiplier = 1
        user_class = "casual attendee"
        folder = folder = (
            f'{config["download"]["root_directory"]}/{formatters.folder_name(id=user, config=config, contacts=contacts, authed_slack_users=authed_slack_users_local)}/{config["download"]["folder_name"]}/'
        )
    # We split off here because we don't want to check for temporary auths if we don't need to
    else:
        temp_auths = auth.get_auths(config=config)
        # Check if the user has an existing temporary auth
        if user in temp_auths:
            multiplier = 0.5
            user_class = "unregistered casual user"
            folder = f'{config["download"]["root_directory"]}/{config["download"]["folder_name"]}/{temp_auths[user]["name"]}.{user}/'
        else:
            multiplier = 0
            user_class = "denied"
            folder = ""
    return {"multiplier": multiplier, "user_class": user_class, "folder": folder}


def is_virus(content=None, hash=None, config=None):
    if not config:  # type: ignore
        raise Exception("Global variable config not created")

    if not content and not hash:
        raise Exception("Must provide either content or hash")

    if content and hash:
        raise Exception("Must provide either content or hash, not both")

    file_hash = None

    if content:
        # Get the file hash
        file_hash = hashlib.sha256(content).hexdigest()

    elif hash:
        file_hash = hash

    if not file_hash:
        raise Exception("File hash could not be calculated")

    # Query VirusTotal
    headers = headers = {
        "accept": "application/json",
        "x-apikey": config["virustotal"]["api_key"],
    }

    response = requests.get(
        f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers
    ).json()

    if response.get("error", None):
        if response["error"]["code"] == "NotFoundError":
            return False

    if response["data"]["attributes"]["reputation"] < 0:
        return response["data"]["attributes"]["meaningful_name"]

    return False
