def shame_ask(name):
    db = db_connect()
    cursor = db.cursor()
    try:
        cursor.execute('''
            SELECT shame FROM people WHERE name=%(name)s
            ''', (name, ))
        shame = cursor.fetchone()
        db.close()
        if shame is None:
            logger.debug('No shame found for name {}'.format(name))
            return shame
        else:
            shame = shame[0]
            logger.debug('shame of {} found for name {}'.format(shame, name))
            return shame
    except Exception as e:
        logger.error('Execution failed with error: {}'.format(e))
        raise
