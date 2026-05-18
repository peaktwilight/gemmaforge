    def set_language(self, lang):
        """
        Update language of user in the User object and in the database
        :param lang: string with language tag like "en-US"
        :return: None
        """
        log.debug('Updating info about user %s language '
                  'in memory & database...', self)

        self.language = lang

        query = ("UPDATE users "
                 f"SET language=%s "
                 f"WHERE chat_id=%s")

        parameters = self.language, self.chat_id
        try:
            db.add(query, parameters)
        except DatabaseError:
            log.error("Can't add new language of %s to the database", self)
        else:
            log.debug('Language updated.')
