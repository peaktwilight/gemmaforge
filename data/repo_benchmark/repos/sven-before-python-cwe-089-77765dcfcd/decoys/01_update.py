def update_theory_base(tag, link):
    theory = sqlite3.connect(os.path.abspath(os.path.dirname(__file__)) + "\\theory.db")
    conn = theory.cursor()
    conn.execute("insert into ? values (?)", (tag, str(link)))
    theory.commit()
    theory.close()
