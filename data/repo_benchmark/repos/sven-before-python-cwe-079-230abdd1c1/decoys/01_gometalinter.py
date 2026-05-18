    def _normalize(self, metaerrors):
        """Normalize output format to be usable by Anaconda's linting frontend
        """

        errors = []
        for error in metaerrors:
            last_path = os.path.join(
                os.path.basename(os.path.dirname(self.filepath)),
                os.path.basename(self.filepath)
            )
            if last_path not in error.get('path', ''):
                continue

            error_type = error.get('severity', 'X').capitalize()[0]
            if error_type == 'X':
                continue
            if error_type not in ['E', 'W']:
                error_type = 'V'
            errors.append({
                'underline_range': True,
                'lineno': error.get('line', 0),
                'offset': error.get('col', 0),
                'raw_message': error.get('message', ''),
                'code': 0,
                'level': error_type,
                'message': '[{0}] {1} ({2}): {3}'.format(
                    error_type,
                    error.get('linter', 'none'),
                    error.get('severity', 'none'),
                    error.get('message')
                )
            })

        return errors
