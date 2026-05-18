    def _exec_cmd(self, cmd):
        """Executes adb commands in a new shell.

        This is specific to executing adb binary because stderr is not a good
        indicator of cmd execution status.

        Args:
            cmds: A string that is the adb command to execute.

        Returns:
            The output of the adb command run if exit code is 0.

        Raises:
            AdbError is raised if the adb command exit code is not 0.
        """
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        ret = proc.returncode
        logging.debug('cmd: %s, stdout: %s, stderr: %s, ret: %s', cmd, out,
                      err, ret)
        if ret == 0:
            return out
        else:
            raise AdbError(cmd=cmd, stdout=out, stderr=err, ret_code=ret)
