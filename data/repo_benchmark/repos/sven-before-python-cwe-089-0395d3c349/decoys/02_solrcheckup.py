def update_history_and_sourcebyinstitution(conn, sqlite, k10plus, ai):
    """
    Get all current sources and title numbers from Solr and log them into database.
    """
    current_sources = get_all_current_sources(k10plus, ai)
    current_institutions = get_all_current_institutions(k10plus, ai)
    old_sourcebyinstitutions = get_all_old_sourcebyinstitutions(conn, sqlite)
    current_sourcebyinstitutions = []

    for source in current_sources:

        for institution in current_institutions:

            if not institution or institution == " " or '"' in institution:
                continue

            sourcebyinstitution = "SID " + str(source) + " (" + institution + ")"
            current_sourcebyinstitutions.append(sourcebyinstitution)

            params = {
                "q": 'source_id:%s AND institution:"%s"' % (source, institution),
                "rows": 0,
                "wt": "json"
            }

            # check k10plus
            result = get_solr_result(k10plus, params)
            number = result["response"]["numFound"]
            if number != 0:
                sql = 'INSERT INTO history (sourcebyinstitution, titles) VALUES (?, ?)'
                sqlite.execute(sql, (sourcebyinstitution, number))
                conn.commit()
            else:
                # check ai
                result = get_solr_result(ai, params)
                number = result["response"]["numFound"]
                if number != 0:
                    # TODO: escape via sqlite
                    sql = 'INSERT INTO history (sourcebyinstitution, titles) VALUES (?, ?)'
                    sqlite.execute(sql, (sourcebyinstitution, number))
                    conn.commit()

            if sourcebyinstitution not in old_sourcebyinstitutions:
                logging.info("The %s is now connected to SID %s.", institution, source)
                sql = "INSERT INTO sourcebyinstitution (sourcebyinstitution) VALUES (?)"
                sqlite.execute(sql, (sourcebyinstitution))
                conn.commit()

            if number != 0:
                old_sourcebyinstitution_number = get_old_sourcebyinstitution_number(conn, sqlite, sourcebyinstitution)
                if number < old_sourcebyinstitution_number:
                    message = "Die Anzahl der Titel hat sich bei %s gegenueber einem frueheren Import verringert." % (sourcebyinstitution)
                    send_message(message)

            # requests.exceptions.ConnectionError: HTTPConnectionPool(XXXXXX): Max retries exceeded
            time.sleep(0.25)

    for old_sourcebyinstitution in old_sourcebyinstitutions:
        if old_sourcebyinstitution not in current_sourcebyinstitutions:
            message = "Die %s ist nicht laenger für die SID %s angesigelt." % (institution, source)
            send_message(message)
