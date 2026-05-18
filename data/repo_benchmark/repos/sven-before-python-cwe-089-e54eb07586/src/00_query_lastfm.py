    def tag_to_tag_num(self, tag):
        ''' Returns tag_num given tag. '''

        q = "SELECT rowid FROM tags WHERE tag = '" + tag + "'"
        self.query(q)
        return self.c.fetchone()[0]
