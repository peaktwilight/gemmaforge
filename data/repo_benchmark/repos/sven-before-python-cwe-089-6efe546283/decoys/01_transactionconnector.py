    def save_accepted_transaction(self, user_id, project_id, money):
        self.cursor.execute("update users set money = money - %s where id = %s", (money, user_id))
        self.cursor.execute("update projects set money = money + %s where id = %s", (money, project_id))
        self.cursor.execute("insert into transactions (project_id, user_id, money, timestamp, state) values (%s, %s, "
                            "%s, now(), 'accepted' )", (project_id, user_id, money))
        self.db.commit()
