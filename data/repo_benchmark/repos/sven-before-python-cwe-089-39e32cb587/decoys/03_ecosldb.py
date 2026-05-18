    def add_item(self, item):
        """"Add new item."""
        if self.connection:
            t = (item[0], item[1], )
            self.cursor.execute('insert into item (name, shoppinglistid) values (?, ?)', t)
            self.connection.commit()
