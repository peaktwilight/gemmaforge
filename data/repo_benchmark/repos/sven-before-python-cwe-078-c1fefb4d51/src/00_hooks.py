def get_output(command: str) -> bytes:
    """
    Run a command and return raw output

    :param str command: the command to run
    :returns: the stdout output of the command
    """
    return subprocess.check_output(command.split())
