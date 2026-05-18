    @staticmethod
    def get_last_active_users(limit):
        """
        Get from the database a tuple of users who have been recently using
        the bot
        :param limit: integer that specifies how much users to get
        :return: tuple of tuples with users info
        """
        log.info('Evaluating last active users with date of '
                 'last time when they used bot...')

        # From photo_queries_table2 we take chat_id of the last
        # active users and from 'users' table we take info about these
        # users by chat_id which is a foreign key
        query = ('SELECT p.chat_id, u.first_name, u.nickname, u.last_name, '
                 'u.language '
                 'FROM photo_queries_table2 p '
                 'INNER JOIN users u '
                 'ON p.chat_id = u.chat_id '
                 'GROUP BY u.chat_id, u.first_name, u.nickname, u.last_name, '
                 'u.language '
                 'ORDER BY MAX(time)'
                 f'DESC LIMIT {limit}')

        try:
            cursor = db.execute_query(query)
        except DatabaseConnectionError:
            log.error("Cannot get the last active users because of some "
                      "problems with the database")
            raise

        last_active_users = cursor.fetchall()
        return last_active_users
