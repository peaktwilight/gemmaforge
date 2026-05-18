@login_manager.user_loader
def load_user(s_id):
    email = str(s_id)
    query = 'select * from usr where email like %s'
    cursor = g.conn.execute(query, (email, ))
    user = User()
    for row in cursor:
        user.name = str(row.name)
        user.email = str(row.email)
        break
    return user
