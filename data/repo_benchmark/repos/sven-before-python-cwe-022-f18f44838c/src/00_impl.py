def deleteKey(client):
	"""Deletes the specified key.
	Returns an error if the key doesn't exist
	"""
	global BAD_REQUEST
	global NOT_FOUND

	validateClient(client)

	client_pub_key = loadClientRSAKey(client)
	token_data = decodeRequestToken(request.data, client_pub_key)

	if re.search('[^a-zA-Z0-9]', token_data['key']):
		raise FoxlockError(BAD_REQUEST, 'Invalid key requested')

	try:
		os.remove('keys/%s/%s.key' % (client, token_data['key']))
	except FileNotFoundError:
		raise FoxlockError(NOT_FOUND, "Key '%s' not found" % token_data['key'])

	return "Key '%s' successfully deleted" % token_data['key']
