def send(event, message: "str", app=None, channel= None):
    if not app:
        raise Exception("Global Slack client not initialised")
    
    # Inject channel
    if channel:
        event["channel"] = channel
    
    # Send a threaded message to the user
    app.client.chat_postMessage(
        channel=event["channel"],
        text=message,
        thread_ts=event["ts"],
    )