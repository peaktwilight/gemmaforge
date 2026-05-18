    def change_message(self, new_message, logged_user):
        update_sql = """
            UPDATE Clients
            SET message = ?
            WHERE client_id = ?
        """

        cursor = self.__conn.cursor()

        cursor.execute(update_sql, (new_message, logged_user.get_client_id()))
        self.__conn.commit()
        logged_user.set_message(new_message)
