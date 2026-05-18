    def add_input(self,data):
        connection = self.connect()
        try:
            # The following is a flaw
            query = "INSERT INTO crimes(description) VALUES (%s);"
            with connection.cursor() as cursor:
                cursor.execute(query, data)
                connection.commit()
        finally:
            connection.close()
