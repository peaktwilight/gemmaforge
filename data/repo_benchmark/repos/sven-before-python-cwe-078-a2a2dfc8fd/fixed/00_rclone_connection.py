    def ls(self, data, path):
        credentials = self._formatCredentials(data, name='current')
        command = [
            'rclone',
            'lsjson',
            'current:{}'.format(path),
        ]

        try:
            result = self._execute(command, credentials)
            result = json.loads(result)
            return result
        except subprocess.CalledProcessError as e:
            raise RcloneException(sanitize(str(e)))
