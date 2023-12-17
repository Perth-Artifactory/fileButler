def send(event, message: "str"):
    if not app: # type: ignore
        app = {}
        raise Exception("Global Slack client not initialised")
    
    # Send a threaded message to the user
    app.client.chat_postMessage(
        channel=event["channel"],
        text=message,
        thread_ts=event["ts"],
    )