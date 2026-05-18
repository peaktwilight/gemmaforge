@contextmanager
def run_interactive_shell_command(command, **kwargs):
    """
    Runs a single command in shell and provides stdout, stderr and stdin
    streams.

    This function creates a context manager that sets up the process (using
    `subprocess.Popen()`), returns to caller, closes streams and waits for
    process to exit on leaving.

    Shell execution is disabled by default (so no shell expansion takes place).
    If you want to turn shell execution on, you can pass `shell=True` like you
    would do for `subprocess.Popen()`.

    The process is opened in `universal_newlines` mode by default.

    :param command: The command to run on shell. This parameter can either
                    be a sequence of arguments that are directly passed to
                    the process or a string. A string gets splitted beforehand
                    using `shlex.split()`.
    :param kwargs:  Additional keyword arguments to pass to `subprocess.Popen`
                    that is used to spawn the process (except `stdout`,
                    `stderr`, `stdin` and `universal_newlines`, a `TypeError`
                    is raised then).
    :return:        A context manager yielding the process started from the
                    command.
    """
    if isinstance(command, str):
        command = shlex.split(command)

    process = Popen(command,
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
