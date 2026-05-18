@bot.message_handler(func = lambda message: get_current_state(message.chat.id) == config.States.S_LOGIN.value)
def get_login2(message):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    if bases.createuserbase.check_username(message.text):
        bot.send_message(message.chat.id, "Invalid handle.")
        set_state(message.chat.id, config.States.S_START.value)
        return 0

    conn.execute("select * from users where chat_id = '" + str(message.chat.id) + "'")
    name = conn.fetchone()
    settings.close()
    bases.update.cf_update()
    bases.createuserbase.clean_base(name[1])
    bases.createuserbase.clean_base(message.text)
    bot.send_message(message.chat.id, "Creating base...")
    bases.createuserbase.init_user(message.text, message.chat.id)
    bot.send_message(message.chat.id, "Done!")
    set_state(message.chat.id, config.States.S_START.value)
