    def get_ports(self):
        # First get the active FC ports
        out = self._cli_run('showport', None)

        # strip out header
        # N:S:P,Mode,State,----Node_WWN----,-Port_WWN/HW_Addr-,Type,
        # Protocol,Label,Partner,FailoverState
        out = out[1:len(out) - 2]

        ports = {'FC': [], 'iSCSI': {}}
        for line in out:
            tmp = line.split(',')

            if tmp:
                if tmp[1] == 'target' and tmp[2] == 'ready':
                    if tmp[6] == 'FC':
                        ports['FC'].append(tmp[4])

        # now get the active iSCSI ports
        out = self._cli_run('showport -iscsi', None)

        # strip out header
        # N:S:P,State,IPAddr,Netmask,Gateway,
        # TPGT,MTU,Rate,DHCP,iSNS_Addr,iSNS_Port
        out = out[1:len(out) - 2]
        for line in out:
            tmp = line.split(',')

            if tmp and len(tmp) > 2:
                if tmp[1] == 'ready':
                    ports['iSCSI'][tmp[2]] = {}

        # now get the nsp and iqn
        result = self._cli_run('showport -iscsiname', None)
        if result:
            # first line is header
            # nsp, ip,iqn
            result = result[1:]
            for line in result:
                info = line.split(",")
                if info and len(info) > 2:
                    if info[1] in ports['iSCSI']:
                        nsp = info[0]
                        ip_addr = info[1]
                        iqn = info[2]
                        ports['iSCSI'][ip_addr] = {'nsp': nsp,
                                                   'iqn': iqn
                                                   }

        LOG.debug("PORTS = %s" % pprint.pformat(ports))
        return ports
