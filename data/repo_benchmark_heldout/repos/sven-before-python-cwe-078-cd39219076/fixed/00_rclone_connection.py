    def verify(self, data):
        credentials = self._formatCredentials(data, name='current')
        command = [
            'rclone',
            'lsjson',
            'current:',
        ]

        try:
            result = self._execute(command, credentials)
            return {
                'result': True,
                'message': 'Success',
            }
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            return {
                'result': False,
                'message': 'Exit status {}'.format(returncode),
            }
