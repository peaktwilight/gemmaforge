def update_institutions(conn, sqlite, k10plus, ai):
    """
    Update the institution table.
    """
    current_institutions = get_all_current_institutions(k10plus, ai)
    old_institutions = get_all_old_institutions(conn, sqlite)

    # Check if the institution table is allready filled and this is not the first checkup
    institution_table_is_filled = len(old_institutions) > 10

    for old_institution in old_institutions:
        if institution_table_is_filled and old_institution not in current_institutions:
            message = "Die ISIL %s ist im aktuellen Import nicht mehr vorhanden.\nWenn dies beabsichtigt ist, bitte die Institution aus der Datenbank loeschen." % old_institution
            send_message(message)

    for current_institution in current_institutions:
        if current_institution == " " or '"' in current_institution:
                continue
        if current_institution not in old_institutions:
            message = "The institution %s is new in Solr." % current_institution
            if institution_table_is_filled:
                send_message(message)
            else:
                logging.info(message)
            sql = "INSERT INTO institution (institution) VALUES ('%s')" % current_institution
            sqlite.execute(sql)
            conn.commit()
