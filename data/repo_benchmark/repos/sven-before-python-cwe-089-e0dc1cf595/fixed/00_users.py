    def cancelFollow(self,userid,friendid):
        sqlText="delete from friends where userid=%d and friendid=%s;"
        params=[userid,friendid]
        result=sql.deleteDB(self.conn,sqlText,params)
        return result;
