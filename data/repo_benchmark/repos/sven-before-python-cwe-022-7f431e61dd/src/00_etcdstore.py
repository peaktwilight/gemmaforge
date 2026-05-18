    def get(self, key):
        try:
            result = self.etcd.get(os.path.join(self.namespace, key))
        except etcd.EtcdException as err:
            log_error("Error fetching key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to get key')
        return result.value
