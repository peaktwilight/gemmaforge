def install(filename, target):
  '''Run a package's installer script against the given target directory.'''
  print(' Unpacking %s...' % filename)
  os.system('tar xf ' + filename)
  basename = filename.split('.tar')[0]
  print(' Installing %s...' % basename)
  install_opts = '--prefix=${PWD}/%s --disable-ldconfig' % target
  os.system('%s/install.sh %s' % (basename, install_opts))
  print(' Cleaning %s...' % basename)
  os.system('rm -rf %s' % basename)
