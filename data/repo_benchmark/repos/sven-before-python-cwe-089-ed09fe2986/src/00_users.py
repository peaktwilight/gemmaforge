    @staticmethod
    def compare_and_update(user, message):
        """
        This method compare a user object from the bot and his info from
        the Telegram message to check whether a user has changed his bio
        or not. If yes, the user object that represents him in the bot will
        be updated accordingly. Now this function is called only when a user
        asks the bot for showing the most popular cams

        :param user: user object that represents a Telegram user in this bot
        :param message: object from Telegram that contains info about user's
        message and about himself
        :return: None
        """

        log.info('Checking whether user have changed his info or not...')
        msg = message.from_user
        usr_from_message = User(message.chat.id, msg.first_name, msg.username,
                                msg.last_name)

        if user.chat_id != usr_from_message.chat_id:
            log.error("Wrong user to compare!")
            return

        if user.first_name != usr_from_message.first_name:
            user.first_name = usr_from_message.first_name

        elif user.nickname != usr_from_message.nickname:
            user.nickname = usr_from_message.nickname

        elif user.last_name != usr_from_message.last_name:
            user.last_name = usr_from_message.last_name

        else:
            log.debug("User's info hasn't changed")
            return

        log.info("User has changed his info")
        log.debug("Updating user's info in the database...")
        query = (f"UPDATE users "
                 f"SET first_name='{user.first_name}', "
                 f"nickname='{user.nickname}', "
                 f"last_name='{user.last_name}' "
                 f"WHERE chat_id={user.chat_id}")

        try:
            db.add(query)
        except DatabaseError:
            log.error("Could not update info about %s in the database",
                      user)
        else:
            log.debug("User's info has been updated")
