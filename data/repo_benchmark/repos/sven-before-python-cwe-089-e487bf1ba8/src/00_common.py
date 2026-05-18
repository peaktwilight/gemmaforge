def get_game_info(conn, game):
    # get the basic game properties
    cursor = conn.cursor()
    cursor.execute("SELECT player1,player2,size,state FROM games WHERE id = %d;" % game)
    if cursor.rowcount != 1:
        raise FormError("Invalid game ID")

    row = cursor.fetchall()[0]
    players = [row[0],row[1]]
    size    =  row[2]
    state   =  row[3]

    if state is None:
         state = "Active"

    cursor.close()

    return (players,size,state)
