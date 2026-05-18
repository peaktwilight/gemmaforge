    def post(self):
        """ Returns JWT upon login verification """
        json_data = request.get_json()
        if not json_data['email']:
            return jsonify({"msg": "Missing email"}), 400

        data = database_utilities.execute_query(
            f"""select * from admins where email = '{json_data['email']}'""")
        if data:
            email = data[0]['email']
            access_token = create_access_token(identity=email)
            refresh_token = create_refresh_token(identity=email)

            resp = jsonify({"login": True})
            set_access_cookies(resp, access_token)
            set_refresh_cookies(resp, refresh_token)
            return resp
        else:
            return jsonify({"msg": "User is not an admin"})
