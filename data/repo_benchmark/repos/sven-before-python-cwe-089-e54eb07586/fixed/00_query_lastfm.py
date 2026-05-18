    def tag_to_tag_num(self, tag):
        ''' Returns tag_num given tag. '''

        q = "SELECT rowid FROM tags WHERE tag = ?"
        self.query(q, tag)
        return self.c.fetchone()[0]
