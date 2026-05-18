    def insertData(self,userid,post):
        sqlText="insert into post(userid,date,comment) \
                values(%s,current_timestamp(0),%s);"
        params=[userid,post];
        result=sql.insertDB(self.conn,sqlText,params)
        return result;
