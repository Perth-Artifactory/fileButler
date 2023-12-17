def send(event, message: "str", app=None, channel=None, ts=None):
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
    )

    return response.data["ts"]
