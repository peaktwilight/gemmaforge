def addKey(client):
	"""Adds a new key with the specified name and contents.
	Returns an error if a key with the specified name already exists.
	"""
	global BAD_REQUEST
	global CREATED

	validateClient(client)

	client_pub_key = loadClientRSAKey(client)
	token_data = decodeRequestToken(request.data, client_pub_key)
	validateNewKeyData(token_data)

	# Use 'x' flag so we can throw an error if a key with this name already exists
	try:
		with open('keys/%s/%s.key' % (client, token_data['name']), 'x') as f:
			f.write(token_data['key'])
	except FileExistsError:
		raise FoxlockError(BAD_REQUEST, "Key '%s' already exists" % token_data['name'])

	return 'Key successfully created', CREATED
