def update_sources(conn, sqlite, k10plus, ai):
    """
    Update the source table.
    """
    current_sources = get_all_current_sources(k10plus, ai)
    old_sources = get_all_old_sources(conn, sqlite)

    # Check if the source table is allready filled and this is not the first checkup
    source_table_is_filled = len(old_sources) > 100

    for old_source in old_sources:
        if source_table_is_filled and old_source not in current_sources:
            message = "Die SID %s ist im aktuellen Import nicht mehr vorhanden.\nWenn dies beabsichtigt ist, bitte die SID aus der Datenbank loeschen." % old_source
            send_message(message)

    for current_source in current_sources:
        if current_source not in old_sources:
            message = "The source %s is new in Solr." % current_source
            if source_table_is_filled:
                send_message(message)
            else:
                logging.info(message)
            sql = "INSERT INTO source (source) VALUES (%s)" % current_source
            sqlite.execute(sql)
            conn.commit()
