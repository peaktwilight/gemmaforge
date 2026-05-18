    def add_item(self, item):
        """"Add new item."""
        if self.connection:
            self.cursor.execute('insert into item (name, shoppinglistid) values ("%s", "%s")' % (item[0], item[1]))
            self.connection.commit()
