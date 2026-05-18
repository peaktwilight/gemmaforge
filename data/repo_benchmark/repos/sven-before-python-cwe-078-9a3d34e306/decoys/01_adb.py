    def _exec_cmd(self, args, shell):
        """Executes adb commands.

        Args:
            args: string or list of strings, program arguments.
                See subprocess.Popen() documentation.
            shell: bool, True to run this command through the system shell,
                False to invoke it directly. See subprocess.Popen() docs.

        Returns:
            The output of the adb command run if exit code is 0.

        Raises:
            AdbError is raised if the adb command exit code is not 0.
        """
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        (out, err) = proc.communicate()
        ret = proc.returncode
        logging.debug('cmd: %s, stdout: %s, stderr: %s, ret: %s', args, out,
                      err, ret)
        if ret == 0:
            return out
        else:
            raise AdbError(cmd=args, stdout=out, stderr=err, ret_code=ret)
