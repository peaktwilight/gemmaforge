    @staticmethod
    def _add_to_db(user):
        """
        Adds User object to the database
        :param user: User object with info about user
        :return: None
        """
        query = ("INSERT INTO users (chat_id, first_name, nickname, "
                 "last_name, language) "
                 f"VALUES ({user.chat_id}, '{user.first_name}', "
                 f"'{user.nickname}', '{user.last_name}', '{user.language}')")
        try:
            db.add(query)
        except DatabaseError:
            log.error("Cannot add user to the database")
        else:
            log.info(f"User {user} was successfully added to the users db")
