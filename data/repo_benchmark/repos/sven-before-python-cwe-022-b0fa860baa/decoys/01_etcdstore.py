    def list(self, keyfilter='/'):
        path = self._absolute_key(keyfilter)
        if path != '/':
            path = path.rstrip('/')
        try:
            result = self.etcd.read(path, recursive=True)
        except etcd.EtcdKeyNotFound:
            return None
        except etcd.EtcdException as err:
            log_error("Error listing %s: [%r]" % (keyfilter, repr(err)))
            raise CSStoreError('Error occurred while trying to list keys')

        value = set()
        for entry in result.get_subtree():
            if entry.key == path:
                continue
            name = entry.key[len(path):]
            if entry.dir and not name.endswith('/'):
                name += '/'
            value.add(name.lstrip('/'))
        return sorted(value)
