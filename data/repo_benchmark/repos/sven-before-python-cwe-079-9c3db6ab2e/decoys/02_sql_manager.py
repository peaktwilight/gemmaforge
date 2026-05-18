    def login(self, username, password):
        select_query = """
            SELECT client_id, username, balance, message
            FROM Clients
            WHERE username = ? AND password = ?
            LIMIT 1
        """

        cursor = self.__conn.cursor()

        cursor.execute(select_query, (username, password))
        user = cursor.fetchone()

        if(user):
            return Client(user[0], user[1], user[2], user[3])
        else:
            return False
