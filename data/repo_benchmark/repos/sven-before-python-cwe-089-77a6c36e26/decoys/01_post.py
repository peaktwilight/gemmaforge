    def getPostsByPostid(self,postid):
        sqlText="select users.name,post.comment from users,post where \
                users.userid=post.userid and post.postid=%s"
        params=[postid]
        result=sql.queryDB(self.conn,sqlText,params)
        return result;
