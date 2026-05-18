    def mkdir(self, data, path):
        credentials = self._formatCredentials(data, name='current')

        command = (
            '{credentials} '
            'rclone touch current:{path}/.keep'
        ).format(
            credentials=credentials,
            path=path,
        )

        try:
            result = self._execute(command)
            return {
                'message': 'Success',
            }
        except subprocess.CalledProcessError as e:
            raise RcloneException(sanitize(str(e)))
