    def add_language(self, language):
        """"Add new language for item translations."""
        if self.connection:
            t = (language[0], )
            self.cursor.execute('insert into itemlanguage (language) values (?)', t)
            self.connection.commit()
