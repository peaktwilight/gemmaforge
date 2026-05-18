def karma_ask(name):
    db = db_connect()
    cursor = db.cursor()
    try:
        cursor.execute(
            ''' SELECT karma FROM people WHERE name='{}' '''.format(name))
        karma = cursor.fetchone()
        if karma is None:
            logger.debug('No karma found for name {}'.format(name))
            db.close()
            return karma
        else:
            karma = karma[0]
            logger.debug('karma of {} found for name {}'.format(karma, name))
            db.close()
            return karma
    except Exception as e:
        logger.error('Execution failed with error: {}'.format(e))
        raise
