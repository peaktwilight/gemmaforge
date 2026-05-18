def karma_add(name):
    karma = karma_ask(name)
    db = db_connect()
    cursor = db.cursor()
    if karma is None:
        try:
            cursor.execute('''
                INSERT INTO people(name,karma,shame) VALUES(%(name)s,1,0)
                ''', name)
            db.commit()
            logger.debug('Inserted into karmadb 1 karma for {}'.format(name))
            return 1
        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise
    else:
        karma = karma + 1
        try:
            cursor.execute('''
                UPDATE people SET karma = %(karma)s WHERE name = %(name)s
                ''', (karma, name))
            db.commit()
            logger.debug('Inserted into karmadb {} karma for {}'.format(
                karma,
                name,
            ))
            return karma

        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise
    db.close()
