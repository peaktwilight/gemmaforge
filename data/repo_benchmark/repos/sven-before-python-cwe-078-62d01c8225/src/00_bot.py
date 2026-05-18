def whitelist(users: str):
    for user in users.split():
        call(WHITELIST_COMMAND_TEMPLATE.format(user))
