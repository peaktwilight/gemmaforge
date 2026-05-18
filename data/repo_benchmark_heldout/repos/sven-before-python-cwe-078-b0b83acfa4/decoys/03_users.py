    def followFriends(self,userid,friendid):
        sqlText="insert into friends values(%s,%s);"
        params=[friendid,userid]
        result=sql.insertDB(self.conn,sqlText,params)
        return result;
