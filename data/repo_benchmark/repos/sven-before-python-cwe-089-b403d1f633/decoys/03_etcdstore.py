    def cut(self, key):
        try:
            self.etcd.delete(self._absolute_key(key))
        except etcd.EtcdKeyNotFound:
            return False
        except etcd.EtcdException as err:
            log_error("Error removing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to cut key')
        return True
