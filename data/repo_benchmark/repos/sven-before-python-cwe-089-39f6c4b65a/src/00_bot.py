def set_state(chat_id, value):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("update users set state ='" + str(value) + "' where chat_id = '" + str(chat_id) + "'")
    settings.commit()
    settings.close()
