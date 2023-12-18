import logging
from typing import Any

from slack_sdk.web.client import WebClient  # for typing

from . import formatters

# Set up logging

logger = logging.getLogger("formatters")


def send(
    event, message: "str", app=None, channel=None, ts=None, broadcast=False, dm=False
):
    if not app:
        raise Exception("Global Slack client not connected")

    event = dict(event)
    if type(event["user"]) != str:
        user = event["user"]["id"]
    else:
        user = event["user"]

    # Inject ts
    if ts:
        event["ts"] = ts

    # Inject channel
    if channel:
        event["channel"] = channel

    # iF
    if not event.get("ts", False) and not channel:
        # Open a DM with the user
        response = app.client.conversations_open(users=user)
        channel = response.data["channel"]["id"]

        # Send an unthreaded message to the user
        response = app.client.chat_postMessage(
            channel=channel, text=message, reply_broadcast=broadcast
        )

    elif channel:
        # Send an unthreaded message to the channel
        response = app.client.chat_postMessage(channel=channel, text=message)

    else:
        # Send a threaded message to the user
        response = app.client.chat_postMessage(
            channel=event["channel"],
            text=message,
            thread_ts=event["ts"],
            reply_broadcast=broadcast,
        )

    return response.data["ts"]


def check_unlimited(user, config, app=None, client=None):
    if app:
        r = app.client.usergroups_list(include_users=True)
    elif client:
        r = client.usergroups_list(include_users=True)
    else:
        raise Exception("Must provide either app or client")

    groups: list[dict[str, Any]] = r.data["usergroups"]
    for group in groups:
        if group["id"] in config["slack"]["unlimited_groups"]:
            if user in group["users"]:
                return True
    return False


def updateHome(
    user: str,
    client: WebClient,
    config,
    authed_slack_users,
    contacts,
    current_members,
    auth_step=None,
) -> None:
    home_view = {
        "type": "home",
        "blocks": formatters.home(
            user=user,
            config=config,
            authed_slack_users=authed_slack_users,
            contacts=contacts,
            client=client,
            current_members=current_members,
            auth_step=auth_step,
        ),
    }
    client.views_publish(user_id=user, view=home_view)


def get_name(id, client: WebClient) -> str:
    r = client.users_info(user=id)
    return r.data["user"]["profile"]["display_name"]  # type: ignore
