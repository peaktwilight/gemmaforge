def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO playsRecord (winner, loser) VALUES ('%s', '%s')" % (winner, loser));
    conn.commit()
    conn.close()
