    def getCommentsLike(self,commentid):
        sqlText="select userid from comment_like where commentid=%d"%(commentid)
        result=sql.queryDB(self.conn,sqlText)
        return result;
