    def tag_num_to_tag(self, tag_num):
        ''' Returns tag given tag_num. '''

        q = "SELECT tag FROM tags WHERE rowid = '" + str(tag_num) + "'"
        self.query(q)
        return self.c.fetchone()[0]
