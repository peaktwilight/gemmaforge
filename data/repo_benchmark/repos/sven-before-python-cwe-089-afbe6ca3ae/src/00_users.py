    def get(self, user_id):
        """ Fetch data for user with corresponding user_id """
        return database_utilities.execute_query(f"""select * from users where user_id = '{user_id}'""")
