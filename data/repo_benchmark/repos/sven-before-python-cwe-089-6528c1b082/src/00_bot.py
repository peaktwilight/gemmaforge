@bot.message_handler(commands =['login'])
def get_login(message):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("select * from users where chat_id = '" + str(message.chat.id) + "'")
    name = conn.fetchone()
    if name != None:
        bot.send_message(message.chat.id, "Previous handle: " + str(name[1]))
    else:
        bot.send_message(message.chat.id, "Previous handle: None")
    settings.close()
    bot.send_message(message.chat.id, "Type new handle: ")
    set_state(message.chat.id, config.States.S_LOGIN.value)
