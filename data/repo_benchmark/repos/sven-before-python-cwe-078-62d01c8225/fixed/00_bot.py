def whitelist(channel: discord.TextChannel, users: str):
    for user in users.split():
        if not re.match(r'^[A-Za-z0-9_]{3,16}$', user):  # as per https://help.mojang.com/customer/en/portal/articles/928638-minecraft-usernames?b_id=5408
            await channel.send('\'{}\' is not a valid Minecraft username'.format(user))
        else:
            call(WHITELIST_COMMAND_TEMPLATE.format(user))
