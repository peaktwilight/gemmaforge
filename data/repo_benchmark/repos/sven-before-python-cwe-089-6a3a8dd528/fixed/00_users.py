    @staticmethod
    def _add_to_db(user):
        """
        Adds User object to the database
        :param user: User object with info about user
        :return: None
        """
        query = ("INSERT INTO users (chat_id, first_name, nickname, "
                 "last_name, language) "
                 f"VALUES (%s, %s, %s, %s, %s)")

        parameters = (user.chat_id, user.first_name, user.nickname,
                      user.last_name, user.language)

        try:
            db.add(query, parameters)
        except DatabaseError:
            log.error("Cannot add user to the database")
        else:
            log.info(f"User {user} was successfully added to the users db")
