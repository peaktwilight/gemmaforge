    def likeComments(self,commentid,userid):
        sqlText="insert into comment_like values(%s,%s);"
        params=[userid,commentid]
        result=sql.insertDB(self.conn,sqlText,params)
        return result;
