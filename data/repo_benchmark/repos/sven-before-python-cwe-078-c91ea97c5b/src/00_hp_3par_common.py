    def _get_3par_host(self, hostname):
        out = self._cli_run('showhost -verbose %s' % (hostname), None)
        LOG.debug("OUTPUT = \n%s" % (pprint.pformat(out)))
        host = {'id': None, 'name': None,
                'domain': None,
                'descriptors': {},
                'iSCSIPaths': [],
                'FCPaths': []}

        if out:
            err = out[0]
            if err == 'no hosts listed':
                msg = {'code': 'NON_EXISTENT_HOST',
                       'desc': "HOST '%s' was not found" % hostname}
                raise hpexceptions.HTTPNotFound(msg)

            # start parsing the lines after the header line
            for line in out[1:]:
                if line == '':
                    break
                tmp = line.split(',')
                paths = {}

                LOG.debug("line = %s" % (pprint.pformat(tmp)))
                host['id'] = tmp[0]
                host['name'] = tmp[1]

                portPos = tmp[4]
                LOG.debug("portPos = %s" % (pprint.pformat(portPos)))
                if portPos == '---':
                    portPos = None
                else:
                    port = portPos.split(':')
                    portPos = {'node': int(port[0]), 'slot': int(port[1]),
                               'cardPort': int(port[2])}

                paths['portPos'] = portPos

                # If FC entry
                if tmp[5] == 'n/a':
                    paths['wwn'] = tmp[3]
                    host['FCPaths'].append(paths)
                # else iSCSI entry
                else:
                    paths['name'] = tmp[3]
                    paths['ipAddr'] = tmp[5]
                    host['iSCSIPaths'].append(paths)

            # find the offset to the description stuff
            offset = 0
            for line in out:
                if line[:15] == '---------- Host':
                    break
                else:
                    offset += 1

            info = out[offset + 2]
            tmp = info.split(':')
            host['domain'] = tmp[1]

            info = out[offset + 4]
            tmp = info.split(':')
            host['descriptors']['location'] = tmp[1]

            info = out[offset + 5]
            tmp = info.split(':')
            host['descriptors']['ipAddr'] = tmp[1]

            info = out[offset + 6]
            tmp = info.split(':')
            host['descriptors']['os'] = tmp[1]

            info = out[offset + 7]
            tmp = info.split(':')
            host['descriptors']['model'] = tmp[1]

            info = out[offset + 8]
            tmp = info.split(':')
            host['descriptors']['contact'] = tmp[1]

            info = out[offset + 9]
            tmp = info.split(':')
            host['descriptors']['comment'] = tmp[1]

        return host
