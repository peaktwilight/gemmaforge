def karma_sub(name):
    karma = karma_ask(name)
    db = db_connect()
    cursor = db.cursor()
    if karma is None:
        try:
            cursor.execute('''
                INSERT INTO people(name,karma,shame) VALUES('{}',-1,0)
                '''.format(name))
            db.commit()
            logger.debug('Inserted into karmadb -1 karma for {}'.format(name))
            db.close()
            return -1

        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise
    else:
        karma = karma - 1
        try:
            cursor.execute('''
                UPDATE people SET karma = {0} WHERE name = '{1}'
                '''.format(karma, name))
            db.commit()
            logger.debug('Inserted into karmadb -1 karma for {}'.format(name))
            db.close()
            return karma
        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise
