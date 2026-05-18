def updateKey(client):
	"""Updates the contents of a key that already exists in our system.
	Returns an error if the specified key doesn't exist for the specified user.
	"""
	global NOT_FOUND
	global CREATED

	validateClient(client)
	client_pub_key = loadClientRSAKey(client)
	token_data = decodeRequestToken(request.data, client_pub_key)
	validateNewKeyData(token_data)
	validateKeyName(token_data['name'])

	# Use 'w' flag to replace existing key file with the new key data
	if os.path.isfile('keys/%s/%s.key' % (client, token_data['name'])):
		with open('keys/%s/%s.key' % (client, token_data['name']), 'w') as f:
			f.write(token_data['key'])
	else:
		raise FoxlockError(NOT_FOUND, "Key '%s' not found" % token_data['name'])

	return 'Key successfully updated', CREATED
