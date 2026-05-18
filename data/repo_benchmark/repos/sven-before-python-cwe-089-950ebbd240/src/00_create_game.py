def process_form():
    # see https://docs.python.org/3.4/library/cgi.html for the basic usage
    # here.
    form = cgi.FieldStorage()


    if "player1" not in form or "player2" not in form or "size" not in form:
        raise FormError("Invalid parameters.")

    player1 = form["player1"].value
    player2 = form["player2"].value
    for c in player1+player2:
        if c not in "_-" and not c.isdigit() and not c.isalpha():
            raise FormError("Invalid parameters: The player names can only contains upper and lowercase characters, digits, underscores, and hypens")
            return

    try:
        size = int(form["size"].value)
    except:
        raise FormError("Invalid parameters: 'size' is not an integer.")
        return

    if size < 2 or size > 9:
        raise FormError("The 'size' must be in the range 2-9, inclusive.")


    # connect to the database
    conn = MySQLdb.connect(host   = pnsdp.SQL_HOST,
                           user   = pnsdp.SQL_USER,
                           passwd = pnsdp.SQL_PASSWD,
                           db     = pnsdp.SQL_DB)
    cursor = conn.cursor()

    # insert the new row
    cursor.execute("""INSERT INTO games(player1,player2,size) VALUES("%s","%s",%d);""" % (player1,player2,size))

    gameID = cursor.lastrowid


    # MySQLdb has been building a transaction as we run.  Commit them now, and
    # also clean up the other resources we've allocated.
    conn.commit()
    cursor.close()
    conn.close()

    return gameID
