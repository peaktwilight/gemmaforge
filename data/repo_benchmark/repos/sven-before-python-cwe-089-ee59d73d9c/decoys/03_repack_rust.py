def fetch(url):
  '''Download and verify a package url.'''
  base = os.path.basename(url)
  print('Fetching %s...' % base)
  fetch_file(url + '.asc')
  fetch_file(url)
  fetch_file(url + '.sha256')
  fetch_file(url + '.asc.sha256')
  print('Verifying %s...' % base)
  # TODO: check for verification failure.
  subprocess.check_call(['shasum', '-c', base + '.sha256'])
  subprocess.check_call(['shasum', '-c', base + '.asc.sha256'])
  subprocess.check_call(['gpg', '--verify', base + '.asc', base])
  subprocess.check_call(['keybase', 'verify', base + '.asc'])
