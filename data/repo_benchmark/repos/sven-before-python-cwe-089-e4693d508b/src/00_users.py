    @jwt_required
    def patch(self, user_id):
        """ Replaces information of corresponding user_id with request body """
        query = f"""update users set user_id = %s """
        query += f"""where user_id = '{user_id}'"""
        json_data = request.get_json()
        parameters = (json_data['user_id'], )
        database_utilities.execute_query(query, parameters)
