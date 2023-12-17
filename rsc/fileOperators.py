import os

def check_folder_eligibility(folder_name: str) -> bool:
    if not config: # type: ignore
        config = {}
        raise Exception("Global variable config not created")
    
    folder = f'{config["download"]["root_directory"]}/{folder_name}/{config["download"]["folder_name"]}/'
    
    # Check if the folder has reached the maximum number of files
    if len(os.listdir(folder)) >= config["download"]["max_folder_files"]:
        return False
    
    # Check if the folder size is over the maximum size
    folder_size = 0
    for file in os.listdir(folder):
        folder_size += os.path.getsize(f'{folder}/{file}')
        if folder_size >= config["download"]["max_folder_size"]:
            return False
    
    return True