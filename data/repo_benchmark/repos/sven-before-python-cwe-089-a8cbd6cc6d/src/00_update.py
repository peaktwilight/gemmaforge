def update_theory_base(tag, link):
    theory = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\theory.db")
    conn = theory.cursor()
    conn.execute("insert into " + str(tag) + " values (?)", (str(link), ))
    theory.commit()
    theory.close()
