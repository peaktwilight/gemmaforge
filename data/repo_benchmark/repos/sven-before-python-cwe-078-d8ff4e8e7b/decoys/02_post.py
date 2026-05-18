    def deletePost(self,postid):
        sqlText="delete from post where post.postid=%s"
        params=[postid]
        result=sql.deleteDB(self.conn,sqlText,params)
        return result;
