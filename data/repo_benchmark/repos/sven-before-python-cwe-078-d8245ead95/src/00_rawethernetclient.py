    def initHeader(self):
        """Initialize the IP header according to the IP format definition.

        """

        # Ethernet header

        # Retrieve remote MAC address
        dstMacAddr = arpreq.arpreq(self.remoteIP)
        if dstMacAddr is not None:
            dstMacAddr = dstMacAddr.replace(':', '')
            dstMacAddr = binascii.unhexlify(dstMacAddr)
        else:
            # Force ARP resolution
            p = subprocess.Popen("ping -c1 {}".format(self.remoteIP), shell=True)
            p.wait()
            time.sleep(0.1)

            dstMacAddr = arpreq.arpreq(self.remoteIP)
            if dstMacAddr is not None:
                dstMacAddr = dstMacAddr.replace(':', '')
                dstMacAddr = binascii.unhexlify(dstMacAddr)
            else:
                raise Exception("Cannot resolve IP address to a MAC address for IP: '{}'".format(self.remoteIP))

        # Retrieve local MAC address
        srcMacAddr = self.get_interface_addr(bytes(self.interface, 'utf-8'))[1]

        eth_dst = Field(name='eth.dst', domain=Raw(dstMacAddr))
        eth_src = Field(name='eth.src', domain=Raw(srcMacAddr))
        eth_type = Field(name='eth.type', domain=Raw(b"\x08\x00"))


        # IP header

        ip_ver = Field(
            name='ip.version', domain=BitArray(
                value=bitarray('0100')))  # IP Version 4
        ip_ihl = Field(name='ip.hdr_len', domain=BitArray(bitarray('0000')))
        ip_tos = Field(
            name='ip.tos',
            domain=Data(
                dataType=BitArray(nbBits=8),
                originalValue=bitarray('00000000'),
                svas=SVAS.PERSISTENT))
        ip_tot_len = Field(
            name='ip.len', domain=BitArray(bitarray('0000000000000000')))
        ip_id = Field(name='ip.id', domain=BitArray(nbBits=16))
        ip_flags = Field(name='ip.flags', domain=Data(dataType=BitArray(nbBits=3), originalValue=bitarray('000'), svas=SVAS.PERSISTENT))
        ip_frag_off = Field(name='ip.fragment', domain=Data(dataType=BitArray(nbBits=13), originalValue=bitarray('0000000000000'), svas=SVAS.PERSISTENT))
        ip_ttl = Field(name='ip.ttl', domain=Data(dataType=BitArray(nbBits=8), originalValue=bitarray('01000000'), svas=SVAS.PERSISTENT))
        ip_proto = Field(name='ip.proto', domain=Integer(value=self.upperProtocol, unitSize=AbstractType.UNITSIZE_8, endianness=AbstractType.ENDIAN_BIG, sign=AbstractType.SIGN_UNSIGNED))
        ip_checksum = Field(name='ip.checksum', domain=BitArray(bitarray('0000000000000000')))
        ip_saddr = Field(name='ip.src', domain=IPv4(self.localIP))
        ip_daddr = Field(
            name='ip.dst', domain=IPv4(self.remoteIP))
        ip_payload = Field(name='ip.payload', domain=Raw())

        ip_ihl.domain = Size([ip_ver,
                              ip_ihl,
                              ip_tos,
                              ip_tot_len,
                              ip_id, ip_flags,
                              ip_frag_off,
                              ip_ttl, ip_proto,
                              ip_checksum,
                              ip_saddr,
                              ip_daddr], dataType=BitArray(nbBits=4), factor=1/float(32))
        ip_tot_len.domain = Size([ip_ver,
                                  ip_ihl,
                                  ip_tos,
                                  ip_tot_len,
                                  ip_id,
                                  ip_flags,
                                  ip_frag_off,
                                  ip_ttl,
                                  ip_proto,
                                  ip_checksum,
                                  ip_saddr,
                                  ip_daddr,
                                  ip_payload], dataType=Integer(unitSize=AbstractType.UNITSIZE_16, sign=AbstractType.SIGN_UNSIGNED), factor=1/float(8))
        ip_checksum.domain = InternetChecksum(fields=[ip_ver,
                                                      ip_ihl,
                                                      ip_tos,
                                                      ip_tot_len,
                                                      ip_id,
                                                      ip_flags,
                                                      ip_frag_off,
                                                      ip_ttl,
                                                      ip_proto,
                                                      ip_checksum,
                                                      ip_saddr,
                                                      ip_daddr], dataType=Raw(nbBytes=2, unitSize=AbstractType.UNITSIZE_16))
        
        self.header = Symbol(name='Ethernet layer', fields=[eth_dst,
                                                            eth_src,
                                                            eth_type,
                                                            ip_ver,
                                                            ip_ihl,
                                                            ip_tos,
                                                            ip_tot_len,
                                                            ip_id,
                                                            ip_flags,
                                                            ip_frag_off,
                                                            ip_ttl,
                                                            ip_proto,
                                                            ip_checksum,
                                                            ip_saddr,
                                                            ip_daddr,
                                                            ip_payload])
