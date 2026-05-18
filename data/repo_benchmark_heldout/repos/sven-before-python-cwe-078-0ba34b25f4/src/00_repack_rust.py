def repack(host, targets, channel='stable'):
  url = 'https://static.rust-lang.org/dist/channel-rust-' + channel + '.toml'
  req = requests.get(url)
  req.raise_for_status()
  manifest = toml.loads(req.content)
  if manifest['manifest-version'] != '2':
    print('ERROR: unrecognized manifest version %s.' % manifest['manifest-version'])
    return
  print('Using manifest for rust %s as of %s.' % (channel, manifest['date']))
  rustc_version, rustc = package(manifest, 'rustc', host)
  if rustc['available']:
    print('rustc %s\n  %s\n  %s' % (rustc_version, rustc['url'], rustc['hash']))
    fetch(rustc['url'])
  cargo_version, cargo = package(manifest, 'cargo', host)
  if cargo['available']:
    print('cargo %s\n  %s\n  %s' % (cargo_version, cargo['url'], cargo['hash']))
    fetch(cargo['url'])
  stds = []
  for target in targets:
      version, info = package(manifest, 'rust-std', target)
      if info['available']:
        print('rust-std %s\n  %s\n  %s' % (version, info['url'], info['hash']))
        fetch(info['url'])
        stds.append(info)
  print('Installing packages...')
  tar_basename = 'rustc-%s-repack' % host
  install_dir = 'rustc'
  os.system('rm -rf %s' % install_dir)
  install(os.path.basename(rustc['url']), install_dir)
  install(os.path.basename(cargo['url']), install_dir)
  for std in stds:
    install(os.path.basename(std['url']), install_dir)
  print('Tarring %s...' % tar_basename)
  os.system('tar cjf %s.tar.bz2 %s/*' % (tar_basename, install_dir))
  os.system('rm -rf %s' % install_dir)
