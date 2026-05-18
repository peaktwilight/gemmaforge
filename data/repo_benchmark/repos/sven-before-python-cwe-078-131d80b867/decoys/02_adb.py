        def adb_call(args=None, shell=False):
            """Wrapper for an ADB command.

            Args:
                args: string or list of strings, arguments to the adb command.
                    See subprocess.Proc() documentation.
                shell: bool, True to run this command through the system shell,
                    False to invoke it directly. See subprocess.Proc() docs.

            Returns:
                The output of the adb command run if exit code is 0.
            """
            args = args or ''
            clean_name = name.replace('_', '-')
            return self._exec_adb_cmd(clean_name, args, shell=shell)
