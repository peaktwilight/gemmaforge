  def update_title(self, title = None):
    if (not self.title):
      self.title = title

    quote_tuple = self.title, self.entry_id

    # This will fall to a sql injection 
    sql = "UPDATE jdk_entries SET title = ?" + \
          "WHERE jdk_entries.id = ?;" 

    db_execute(sql, quote_tuple)
    
    self.update_date_modified()

    return None
