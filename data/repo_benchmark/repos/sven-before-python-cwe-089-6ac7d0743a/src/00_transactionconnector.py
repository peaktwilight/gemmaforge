    def save_failure_transaction(self, user_id, project_id, money):
        self.cursor.execute("insert into transactions (project_id,user_id, money, timestamp, state) values (%s, %s, %s, now(), 'failed' )" % (project_id, user_id, money))
        self.db.commit()
