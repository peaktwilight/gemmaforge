    def getAllComments(self):
        sqlText="select comment from comments where userid=%s order by date;"
        params = [self.userid]
        allposts=sql.queryDB(self.conn,sqlText,params)
        return allposts;
