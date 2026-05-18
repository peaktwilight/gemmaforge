def install(filename, target):
  '''Run a package's installer script against the given target directory.'''
  print(' Unpacking %s...' % filename)
  subprocess.check_call(['tar', 'xf', filename])
  basename = filename.split('.tar')[0]
  print(' Installing %s...' % basename)
  install_cmd = [os.path.join(basename, 'install.sh')]
  install_cmd += ['--prefix=' + os.path.abspath(target)]
  install_cmd += ['--disable-ldconfig']
  subprocess.check_call(install_cmd)
  print(' Cleaning %s...' % basename)
  subprocess.check_call(['rm', '-rf', basename])
