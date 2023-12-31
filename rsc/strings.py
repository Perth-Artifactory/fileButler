not_authed = "This service may only be used remotely by users that have registered with TidyHQ.\nIf you hold, or have previously held, a membership with us then we were unable to automatically link your Slack and TidyHQ accounts. Please contact a committee member for assistance.\nIf you are not registered with TidyHQ you can sign up <{signup_url}|here>."
not_authed_msg_addon = (
    " Alternatively you can request temporary access by clicking on my Home tab."  # No idea why Black messes with this line specifically
)
dm = "Hi there! Click on Home to find out how I work or send me a file to save."
not_authed_admin = "<@{user}> tried to upload a file but is not registered with TidyHQ or their Slack account is not linked."
no_root_directory = "It looks like you don't have a folder in the Member Work directory. Or if you do it's not named `{folder}`. I've created it for you."
no_butler_directory = "It looks like you haven't used me before. When I save files for you I put them in a folder called `folder` inside your folder in the Member Work directory. I've created it for you."
duplicate_file = "`{file}` has been ignored as it already exists in your butler folder. You can find it here: `{folder}/{file}`. To replace it please delete/move the existing file and upload the new version."
file_too_big = "`{file}` is {size}, which is larger than the limit of {max_file_size}. It has been ignored."
over_folder_limit = "`{file}` has been ignored as your butler folder is full. You may only have {max_folder_files} files in your folder, and the total size of your butler folder may not exceed {max_folder_size}. To remedy this please delete/move some files from the {butler_folder} folder to somewhere else in your member directory."
over_folder_limit_admin = "<@{user}> tried to upload `{file}` but their butler folder is full. (Either more than {max_folder_files} files or a total size of more than {max_folder_size}.) It has not been saved.)"
file_saved = "`{file}` has been saved to your butler folder. You can find it here: `{folder}/{file}`"
file_saved_admin = "`{file}` has been saved to <@{user}>'s butler folder. They can find it here: `{folder}/{file}`"
virus_found = "There was a problem uploading your file. Please contact a committee member for assistance."
virus_found_admin = "<@{user}> tried to upload `{file}` which has been flagged as a virus. (`{virus_name}`) It has not been saved."

explainer = "File Butler is a service that allows you to upload files to your Member Work folder from Slack. Files you upload here will be accessible from any workstation in the space. To upload files send them to me as a message and I'll let you know when they're ready."
quota = "As {user_class_prefix} *{user_class}* there are certain limitations on the number and size of files that you can submit via File Butler:\nIndividual file size: {max_file_size}\nButler folder size: {current_folder_size}/{max_folder_size} {folder_size_bar}\nButler folder items: {current_folder_items}/{max_folder_files} {folder_items_bar}"
quota_context = "These limits are specifically on your Butler folder, there's no restriction on the files stored in your overall Member Work folder."
file_item = "• {file} ({size}) - <!date^{epoch}^Uploaded {{date_short_pretty}} at {{time}}|Uploaded {date_str}>"
reset = "If you need to reset this folder you can do so here. This will delete all files submitted via File Butler while leaving everything outside this folder intact."
reset_button = "Reset Folder"
delete_success = "Your Butler folder has been reset."
delete_success_admin = "<@{user}> has reset their Butler folder."
folder_location = "Your Butler folder is located at `{folder}`"

request_auth = "If you're connected to our WiFi network you can gain temporary access to this service. Press the Check button to get started."
request_auth_button = "Check"
request_auth_button_step_2 = "Verify"
