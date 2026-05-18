    def change_pass(self, new_pass, logged_user):
        update_sql = """
            UPDATE Clients
            SET password = ?
            WHERE client_id = ?
        """

        cursor = self.__conn.cursor()

        cursor.execute(update_sql, (new_pass, logged_user.get_client_id()))
        self.__conn.commit()
