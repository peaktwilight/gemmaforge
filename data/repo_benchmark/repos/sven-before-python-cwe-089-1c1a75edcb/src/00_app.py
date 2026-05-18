def add_language(lang):
    try:
        cur.execute(f"INSERT INTO language (name) VALUES ('{lang}')")
    except Exception as e:
        pass
    cur.execute(f"SELECT language_id FROM language where name='{lang}'")
    lang_id = cur.fetchone()[0]
    if conn.commit():
        return lang_id
    return lang_id
