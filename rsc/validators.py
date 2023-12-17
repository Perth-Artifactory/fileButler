from typing import Any, Literal


def check_size(
    id: str | Literal[None] = None,
    file_object: dict[Any, Any] | Literal[None] = None,
    config=None,
) -> int | bool:
    if not config:
        raise Exception("Global variable config not created")

    if not id and not file_object:
        raise Exception("Must provide either id or file_object")
    elif id and file_object:
        raise Exception("Must provide either id or file_object, not both")
    if id:
        # Get the file object from the id
        file: SlackResponse = app.client.files_info(file=id)  # type: ignore
    # Check the file size against the limit specified in config.json
    elif file_object:
        file: dict = file_object

    size: int = file["size"]  # type: ignore
    if size > config["download"]["max_file_size"]:
        return False
    else:
        return int(size)
