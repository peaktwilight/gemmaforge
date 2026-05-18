def populate_custom_grains_and_pillar():
    '''
    Populate local salt-minion grains and pillar fields values as specified in
    config file.

    For example:

        custom_grains_pillar:
          grains:
            - selinux: selinux:enabled
            - release: osrelease
          pillar:
            - ntpserver: network_services:ntpserver

    Note that the core grains are already included in hubble grains -- this
    is only necessary for custom grains and pillar data.
    '''
    log.debug('Fetching custom grains and pillar details')
    grains = {}
    salt.modules.config.__opts__ = __opts__
    custom_grains = __salt__['config.get']('custom_grains_pillar:grains', [])
    for grain in custom_grains:
        for key in grain:
            if _valid_command(grain[key]):
                value = __salt__['cmd.run']('salt-call grains.get {0}'.format(grain[key])).split('\n')[1].strip()
                grains[key] = value
    custom_pillar = __salt__['config.get']('custom_grains_pillar:pillar', [])
    for pillar in custom_pillar:
        for key in pillar:
            if _valid_command(pillar[key]):
                value = __salt__['cmd.run']('salt-call pillar.get {0}'.format(pillar[key])).split('\n')[1].strip()
                grains[key] = value
    log.debug('Done with fetching custom grains and pillar details')
    return grains
