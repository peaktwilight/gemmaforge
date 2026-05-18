  def update_date_modified(self):
    sql = "UPDATE jdk_entries " + \
      "SET date_last_modified = " + CURRENT_DATESTAMP + " " + \
      "WHERE jdk_entries.id = '" + self.entry_id + "';"
    
    db_execute(sql)

    return None
