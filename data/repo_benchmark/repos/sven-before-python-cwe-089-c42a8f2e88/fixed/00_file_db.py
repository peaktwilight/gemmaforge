	def getFileCacheID(self, pth):
		"""
		Returns ID of a cached file on Telegram from DB. None if file doesn't exist or has no cached ID.
		:param pth:
		:return:
		"""
		command = "SELECT file_id FROM {0} WHERE path=?;".format(TABLE_NAME)
		params = (pth,)
		data = self._run_command(command, params)

		try:
			data = data[0][0]
		except IndexError:
			data = None

		return data
