    def tid_num_to_tag_nums(self, tid_num):
        ''' Returns list of the associated tag_nums to the given tid_num. '''

        q = "SELECT tag FROM tid_tag WHERE tid = '" + str(tid_num) + "'"
        self.query(q)
        return [i[0] for i in self.c.fetchall()]
