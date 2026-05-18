    def copy(self, src_data, src_path, dst_data, dst_path, job_id=None):
        credentials = ''

        if src_data is None: # Local
            src = src_path
        else:
            credentials += self._formatCredentials(src_data, name='src')
            src = 'src:{}'.format(src_path)

        if dst_data is None: # Local
            dst = dst_path
        else:
            credentials += self._formatCredentials(dst_data, name='dst')
            dst = 'dst:{}'.format(dst_path)


        command = (
            '{credentials} '
            'rclone copy {src} {dst} '
            '--progress '
            '--stats 2s '
        ).format(
            credentials=credentials,
            src=src,
            dst=dst,
        )

        logging.info(sanitize(command))

        if job_id is None:
            job_id = self._get_next_job_id()
        else:
            if self._job_id_exists(job_id):
                raise ValueError('rclone copy job with ID {} already exists'.fromat(job_id))

        self._stop_events[job_id] = threading.Event()

        try:
            self._execute_interactive(command, job_id)
        except subprocess.CalledProcessError as e:
            raise RcloneException(sanitize(str(e)))

        return job_id
