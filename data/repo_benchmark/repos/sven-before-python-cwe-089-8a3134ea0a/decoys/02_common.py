def build_board(conn, game,size):
    # we'll build the empty board, and then fill in with the move list that
    # we get from the DB.
    board = []
    for i in range(size):
        board.append([""]*size)


    # search for all moves that have happenend during this game.
    cursor = conn.cursor()
    cursor.execute("SELECT x,y,letter FROM moves WHERE gameID = %d;", (game,))

    counts = {"X":0, "O":0}
    for move in cursor.fetchall():
        (x,y,letter) = move

        x = int(x)
        y = int(y)
        assert x >= 0 and x < size
        assert y >= 0 and y < size

        assert letter in "XO"

        assert board[x][y] == ""
        board[x][y] = letter

        counts[letter] += 1

    cursor.close()

    assert counts["X"] >= counts["O"]
    assert counts["X"] <= counts["O"]+1

    if counts["X"] == counts["O"]:
        nextPlayer = 0
    else:
        nextPlayer = 1
    letter = "XO"[nextPlayer]

    return (board,nextPlayer,letter)
