def getKey(client):
	"""Retrieves the specified key for the specified client
	Returns an error if the key doesn't exist, obviously.
	"""
	global SERVER_JWT_PRIVATE_KEY
	global BAD_REQUEST

	validateClient(client)

	client_pub_key = loadClientRSAKey(client)
	token_data = decodeRequestToken(request.data, client_pub_key)

	# Keys may only have alpha-numeric names
	try:
		if re.search('[^a-zA-Z0-9]', token_data['key']):
			raise FoxlockError(BAD_REQUEST, 'Invalid key requested')
		requested_key = open('keys/%s/%s.key' % (client, token_data['key']), 'r').read()
	except KeyError:
		raise FoxlockError(BAD_REQUEST, "JWT did not contain attribute 'key'")
	except IOError:
		raise FoxlockError(BAD_REQUEST, "Key '%s' not found" % token_data['key'])

	# Key is returned in a JWT encrypted with the client's public key, so only they can decrypt it
	keytoken = packJWT({'key': requested_key}, SERVER_JWT_PRIVATE_KEY, client_pub_key)

	return keytoken
