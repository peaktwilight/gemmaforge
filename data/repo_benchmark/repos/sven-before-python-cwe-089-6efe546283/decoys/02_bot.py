def set_state(chat_id, value):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("update users set state = ? where chat_id = ?", (str(value), str(chat_id)))
    settings.commit()
    settings.close()
