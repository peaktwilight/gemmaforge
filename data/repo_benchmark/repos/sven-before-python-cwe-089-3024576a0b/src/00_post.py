    def deletePost(self,postid):
        sqlText="delete from post where post.postid=%d"%(postid)
        result=sql.deleteDB(self.conn,sqlText)
        return result;
