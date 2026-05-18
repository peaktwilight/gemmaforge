    def _checkPairing():
        if winner == loser:
            raise ValueError('Attempt to match player against self')

        q = '''
        SELECT COUNT(*) FROM matches
        WHERE (matches.winner_id = %s AND matches.loser_id = %s)
              OR (matches.winner_id = %s AND matches.loser_id = %s);
        ''' % (winner, loser, loser, winner)
        cur.execute(q)
        if cur.fetchone()[0] > 0:
            raise ValueError('Pairing %s, %s already played' % (winner, loser))
