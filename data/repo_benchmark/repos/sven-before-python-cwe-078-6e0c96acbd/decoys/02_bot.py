@bot.message_handler(commands=['stats'])
def stats(message):
    settings = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\settings.db")
    conn = settings.cursor()
    conn.execute("select * from users where chat_id = ?", (str(message.chat.id),))
    name = conn.fetchone()
    settings.close()
    if name != None:
        bases.update.update_user(name[1], name[0], name[2])
        bases.problem.create_text_stats(name[1])
        img = open(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\users\\" + name[1] + ".png", "rb")
        bot.send_photo(message.chat.id, img)
        img.close()
        if bases.problem.create_stats_picture(name[1]):
            bot.send_message(message.chat.id, "Sorry, you haven't solved tasks.")
            return 0
        img = open(os.path.abspath(os.path.dirname(__file__)) + "\\bases\\users\\" + name[1] + ".png", "rb")
        bot.send_photo(message.chat.id, img)
        img.close()
    else:
        bot.send_message(message.chat.id, "You should login before getting statistic.")
