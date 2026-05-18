    @jwt_required
    def delete(self, user_id):
        """ Deletes user with the corresponding user_id """
        return database_utilities.execute_query(f"""delete from users where user_id = '{user_id}'""")
