@bot.message_handler(func = lambda message: get_current_state(message.chat.id) == config.States.S_GET_TASK.value)
def get_task(message):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("select * from users where chat_id = '" + str(message.chat.id) + "'")
    name = conn.fetchone()
    settings.close()
    if name == None:
        bot.send_message(message.chat.id, "You should login before get tasks.")
    else:
        bases.update.update_user(name[1], name[0], name[2])
        bot.send_message(message.chat.id, bases.problem.get_unsolved_problem(message.text, name[1]))
    set_state(message.chat.id, config.States.S_START.value)
