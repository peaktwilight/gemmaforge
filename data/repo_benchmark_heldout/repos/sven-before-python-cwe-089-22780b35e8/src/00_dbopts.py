def shame_add(name):
    shame = shame_ask(name)
    db = db_connect()
    cursor = db.cursor()
    if shame is None:
        try:
            cursor.execute('''
                INSERT INTO people(name,karma,shame) VALUES('{}',0,1)
                '''.format(name))
            db.commit()
            logger.debug('Inserted into karmadb 1 shame for {}'.format(name))
            db.close()
            return 1
        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise

    else:
        shame = shame + 1
        try:
            cursor.execute('''
                UPDATE people SET shame = {0} WHERE name = '{1}'
                '''.format(shame, name))
            db.commit()
            logger.debug('Inserted into karmadb {} shame for {}'.format(
                shame, name))
            db.close()
            return shame
        except Exception as e:
            logger.error('Execution failed with error: {}'.format(e))
            raise
