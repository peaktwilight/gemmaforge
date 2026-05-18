    def insertData(self,userid,post):
        sqlText="insert into post(userid,date,comment) \
                values(%d,current_timestamp(0),'%s');"%(userid,post);
        result=sql.insertDB(self.conn,sqlText)
        return result;
