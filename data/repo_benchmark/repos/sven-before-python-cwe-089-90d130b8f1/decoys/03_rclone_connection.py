    def mkdir(self, data, path):
        credentials = self._formatCredentials(data, name='current')
        command = [
            'rclone',
            'touch',
            'current:{}/.keep'.format(path),
        ]

        try:
            result = self._execute(command, credentials)
            return {
                'message': 'Success',
            }
        except subprocess.CalledProcessError as e:
            raise RcloneException(sanitize(str(e)))
