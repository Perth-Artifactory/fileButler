from . import strings

divider = [{"type": "divider"}]
explainer = [{"type": "section", "text": {"type": "mrkdwn", "text": strings.explainer}}]
quota = [
    {"type": "section", "text": {"type": "mrkdwn", "text": strings.quota}},
    {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": strings.quota_context,
            }
        ],
    },
]
current_file_list = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "Current files", "emoji": True},
    },
    {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_list",
                "style": "bullet",
                "elements": [],
            }
        ],
    },
]
current_file_list_item = [
    {
        "type": "rich_text_section",
        "elements": [{"type": "text", "text": ""}],
    }
]
current_file_delete = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": strings.reset},
        "accessory": {
            "type": "button",
            "style": "danger",
            "text": {"type": "plain_text", "text": strings.reset_button, "emoji": True},
            "value": "unused",
            "confirm": {
                "title": {"type": "plain_text", "text": "Are you sure?"},
                "text": {
                    "type": "mrkdwn",
                    "text": "This will delete all files in your Butler folder.",
                },
                "confirm": {"type": "plain_text", "text": "Yes, delete them all."},
                "deny": {"type": "plain_text", "text": "No, keep them."},
            },
            "action_id": "purge_folder",
        },
    }
]

not_authed = [
    {"type": "section", "text": {"type": "mrkdwn", "text": strings.not_authed}}
]
folder_location = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": strings.folder_location},
    }
]
text = [{"type": "section", "text": {"type": "mrkdwn", "text": ""}}]
request_auth_step_1 = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": strings.request_auth},
        "accessory": {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": strings.request_auth_button, "emoji": True},
            "value": "unused",
            "action_id": "requesting_auth",
            "url": "",
        },
    }
]
request_auth_step_2 = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": strings.request_auth},
        "accessory": {
            "type": "button",
            "style": "primary",
            "text": {
                "type": "plain_text",
                "text": strings.request_auth_button_step_2,
                "emoji": True,
            },
            "value": "unused",
            "action_id": "refresh_home",
        },
    }
]
