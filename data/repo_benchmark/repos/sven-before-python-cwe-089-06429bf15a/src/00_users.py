    def getAllComments(self):
        sqlText="select comment from comments where userid=%d order by date;"
        allposts=sql.queryDB(self.conn,sqlText)
        return allposts;
