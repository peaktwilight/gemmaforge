    def getCommentsLike(self,commentid):
        sqlText="select userid from comment_like where commentid=%s"
        params=[commentid]
        result=sql.queryDB(self.conn,sqlText,params)
        return result;
