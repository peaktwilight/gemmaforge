@contextmanager
def run_interactive_shell_command(command, **kwargs):
    """
    Runs a command in shell and provides stdout, stderr and stdin streams.

    This function creates a context manager that sets up the process, returns
    to caller, closes streams and waits for process to exit on leaving.

    The process is opened in `universal_newlines` mode.

    :param command: The command to run on shell.
    :param kwargs:  Additional keyword arguments to pass to `subprocess.Popen`
                    that is used to spawn the process (except `shell`,
                    `stdout`, `stderr`, `stdin` and `universal_newlines`, a
                    `TypeError` is raised then).
    :return:        A context manager yielding the process started from the
                    command.
    """
    process = Popen(command,
                    shell=True,
                    stdout=PIPE,
                    stderr=PIPE,
                    stdin=PIPE,
                    universal_newlines=True,
                    **kwargs)
    try:
        yield process
    finally:
        process.stdout.close()
        process.stderr.close()
        process.stdin.close()
        process.wait()
