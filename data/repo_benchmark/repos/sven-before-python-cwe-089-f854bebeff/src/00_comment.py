    def likeComments(self,commentid,userid):
        sqlText="insert into comment_like values(%d,%d);"%(userid,commentid)
        result=sql.insertDB(self.conn,sqlText)
        return result;
