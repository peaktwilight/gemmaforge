	def get_secrets(self, from_date_added=0):
		secrets = []
		for row in self.cursor.execute('SELECT encrypted, json_id, date_added FROM secret WHERE date_added > ? ORDER BY date_added DESC', (from_date_added,)):
			aes_key, json_id, date_added = cryptlib.eciesDecrypt(row[0], self.privkey), row[1], row[2]
			if aes_key != None:
				secrets.append([aes_key, json_id])
			from_date_added = max(from_date_added, date_added)
		return (secrets, from_date_added)
