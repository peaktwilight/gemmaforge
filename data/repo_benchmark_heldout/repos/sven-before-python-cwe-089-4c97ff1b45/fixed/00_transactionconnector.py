    def can_user_pass_that_amount_of_money(self, user_id, money):
        self.cursor.execute("SELECT count(id) FROM kickstarter.users where id = %s and money >= %s", (user_id, money))
        return self.cursor.fetchall()[0][0]
