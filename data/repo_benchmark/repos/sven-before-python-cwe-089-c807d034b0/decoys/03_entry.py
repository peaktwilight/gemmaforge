  def update_date_modified(self):
    quote_tuple = CURRENT_DATESTAMP, self.entry_id

    sql = "UPDATE jdk_entries " + \
      "SET date_last_modified = ? " + \
      "WHERE jdk_entries.id = ?;"
    
    db_execute(sql, quote_tuple)

    return None
