def get_current_state(chat_id):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__))+"\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("select * from users where chat_id = ?", (str(chat_id),))
    name = conn.fetchone()
    if name != None:
        return name[4]
    else:
        return False
    settings.close()
