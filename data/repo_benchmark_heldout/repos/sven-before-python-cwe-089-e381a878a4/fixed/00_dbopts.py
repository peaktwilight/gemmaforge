def also_add(name, also):
    db = db_connect()
    cursor = db.cursor()
    try:
        cursor.execute('''
            INSERT INTO isalso(name,also) VALUES(%(name)s,%(also)s)
            ''', (
            name,
            also,
        ))
        db.commit()
        logger.debug('added to isalso name {} with value {}'.format(
            name, also))
        db.close()
    except Exception as e:
        logger.error('Execution failed with error: {}'.format(e))
        raise
