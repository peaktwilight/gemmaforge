def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    conn = connect()
    cursor = conn.cursor()
    query = "INSERT INTO playsRecord (winner, loser) VALUES (%s, %s);"
    cursor.execute(query, (winner, loser));
    conn.commit()
    conn.close()
