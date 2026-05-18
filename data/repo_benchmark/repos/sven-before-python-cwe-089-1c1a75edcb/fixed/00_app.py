def add_language(lang):
    try:
        cur.execute("INSERT INTO language (name) VALUES (%s)", (lang, ))
    except Exception as e:
        pass
    cur.execute("SELECT language_id FROM language where name=%s", (lang, ))
    lang_id = cur.fetchone()[0]
    if conn.commit():
        return lang_id
    return lang_id
