    def getCommentsByPostid(self,postid,userid):
        sqlText="select (select Count(*) from comment_like where \
        comments.commentid = comment_like.commentid) as like,(select Count(*) \
                from comment_like where comments.commentid = \
                comment_like.commentid and comment_like.userid=%s) as \
                flag,commentid,name,comment from users,comments where \
                users.userid=comments.userid and postid=%s order by date desc;"
        params=[userid,postid]
        result=sql.queryDB(self.conn,sqlText,params)
        return result;
