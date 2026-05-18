def top_karma(bot, trigger):
    """
    Show karma status for the top n number of IRC users.
    """
    try:
        top_limit = int(trigger.group(2).strip())
    except ValueError:
        top_limit = 5

    query = "SELECT slug, value FROM nick_values NATURAL JOIN nicknames \
        WHERE key = 'karma' ORDER BY value DESC LIMIT ?"
    karmalist = bot.db.execute(query, str(top_limit)).fetchall()
    for user in karmalist:
        bot.say("%s == %s" % (user[0], user[1]))
