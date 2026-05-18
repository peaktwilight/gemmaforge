    def followFriends(self,userid,friendid):
        sqlText="insert into friends values(%d,%d);"%(friendid,userid)
        result=sql.insertDB(self.conn,sqlText)
        return result;
