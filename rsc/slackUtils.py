from typing import Any

def send(event, message: "str", app=None, channel=None, ts=None, broadcast=False):
    if not app:
        raise Exception("Global Slack client not initialised")

    event = dict(event)

    # Inject ts
    if ts:
        event["ts"] = ts

    # Inject channel
    if channel:
        event["channel"] = channel

    # Send a threaded message to the user
    response = app.client.chat_postMessage(
        channel=event["channel"],
        text=message,
        thread_ts=event["ts"],
        reply_broadcast=broadcast,
    )

    return response.data["ts"]

def check_unlimited(app, user, config):
    r = app.client.usergroups_list(include_users=True)
    groups: list[dict[str, Any]] = r.data["usergroups"]
    for group in groups:
        if group["id"] in config["slack"]["unlimited_groups"]:
            if user in group["users"]:
                return True
    return False
