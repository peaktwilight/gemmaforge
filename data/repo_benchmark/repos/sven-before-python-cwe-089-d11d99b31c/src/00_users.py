    def userLogin(self):

        sqlName="select count(*) from users where name='%s' and \
                password='%s';"%(self.name,self.password)
        checkName=sql.queryDB(self.conn,sqlName)

        result=checkName[0][0]
        if result == 0:
            self.clean()
            return False
        else:
            return True
