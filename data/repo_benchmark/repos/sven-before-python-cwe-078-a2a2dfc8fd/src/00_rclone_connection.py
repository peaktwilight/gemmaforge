    def ls(self, data, path):
        credentials = self._formatCredentials(data, name='current')

        command = (
            '{credentials} '
            'rclone lsjson current:{path}'
        ).format(
            credentials=credentials,
            path=path,
        )

        try:
            result = self._execute(command)
            result = json.loads(result)
            return result
        except subprocess.CalledProcessError as e:
            raise RcloneException(sanitize(str(e)))
