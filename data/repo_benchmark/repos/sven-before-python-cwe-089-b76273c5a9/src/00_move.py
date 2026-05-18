def process_form():
    # see https://docs.python.org/3.4/library/cgi.html for the basic usage
    # here.
    form = cgi.FieldStorage()


    # connect to the database
    conn = MySQLdb.connect(host   = pnsdp.SQL_HOST,
                           user   = pnsdp.SQL_USER,
                           passwd = pnsdp.SQL_PASSWD,
                           db     = pnsdp.SQL_DB)


    if "user" not in form or "game" not in form:
        raise FormError("Invalid parameters.")
    if "pos" not in form and "resign" not in form:
        raise FormError("Invalid parameters.")

    game = int(form["game"].value)


    (players,size,state) = get_game_info(conn, game)

    user = form["user"].value
    if user not in players:
        raise FormError("Invalid player ID - player is not part of this game")


    if "resign" in form:
        resign = True
    else:
        resign = False
        pos = form["pos"].value.split(",")
        assert len(pos) == 2
        x = int(pos[0])
        y = int(pos[1])


    (board,nextPlayer,letter) = build_board(conn, game,size)

    if user != players[nextPlayer]:
        raise FormError("Internal error, incorrect player is attempting to move.")


    if resign:
        # this user is choosing to resign.  Update the game state to reflect that.
        other_player_name = players[1-nextPlayer]

        cursor = conn.cursor()
        cursor.execute("""UPDATE games SET state="%s:resignation" WHERE id=%d;""" % (other_player_name,game))
        cursor.close()

    else:
        assert x >= 0 and x < size
        assert y >= 0 and y < size

        assert board[x][y] == ""
        board[x][y] = "XO"[nextPlayer]

        # we've done all of our sanity checks.  We now know enough to say that
        # it's safe to add a new move.
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO moves(gameID,x,y,letter,time) VALUES(%d,%d,%d,"%s",NOW());""" % (game,x,y,letter))

        if cursor.rowcount != 1:
            raise FormError("Could not make move, reason unknown.")

        cursor.close()

        result = analyze_board(board)
        if result != "":
            if result == "win":
                result = players[nextPlayer]+":win"

            cursor = conn.cursor()
            cursor.execute("""UPDATE games SET state="%s" WHERE id=%d;""" % (result,game))
            cursor.close()

    # we've made changes, make sure to commit them!
    conn.commit()
    conn.close()


    # return the parms to the caller, so that they can build a good redirect
    return (user,game)
