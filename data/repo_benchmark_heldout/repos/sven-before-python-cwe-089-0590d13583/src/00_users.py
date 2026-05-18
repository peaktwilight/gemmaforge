    def cancelFollow(self,userid,friendid):
        sqlText="delete from friends where userid=%d and friendid=%d;"%(userid,friendid)
        result=sql.deleteDB(self.conn,sqlText)
        return result;
