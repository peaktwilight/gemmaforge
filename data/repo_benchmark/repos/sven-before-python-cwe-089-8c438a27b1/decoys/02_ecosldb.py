    def add_translationname(self, trname):
        """Add new translation by item name for an item."""
        if self.connection:
            for item in self.find_item_name([trname[0], '0']):
                t = (item[0], trname[1], trname[2], )
                self.cursor.execute('insert into itemtranslation (itemid, itemlanguageid, translation) values (?, ?, ?)', t)
            self.connection.commit()
