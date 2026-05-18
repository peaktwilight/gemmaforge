    def clean_cache(self, limit):
        """
        Method that remove several User objects from cache - the least 
        active users
        :param limit: number of the users that the method should remove
        from cache
        :return: None
        """

        log.info('Figuring out the least active users...')
        # Select users that the least active recently
        user_ids = tuple(self.users.keys())
        query = ('SELECT chat_id '
                 'FROM photo_queries_table2 '
                 f'WHERE chat_id in {user_ids} '
                 'GROUP BY chat_id '
                 'ORDER BY MAX(time) '
                 f'LIMIT {limit}')

        try:
            cursor = db.execute_query(query)
        except DatabaseConnectionError:
            log.error("Can't figure out the least active users...")
            return

        if not cursor.rowcount:
            log.warning("There are no users in the db")
            return

        # Make list out of tuple of tuples that is returned by MySQL
        least_active_users = [chat_id[0] for chat_id in cursor.fetchall()]
        log.info('Removing %d least active users from cache...', limit)
        num_deleted_entries = 0
        for entry in least_active_users:
            log.debug('Deleting %s...', entry)
            deleted_entry = self.users.pop(entry, None)
            if deleted_entry:
                num_deleted_entries += 1
        log.debug("%d users were removed from cache.", num_deleted_entries)
