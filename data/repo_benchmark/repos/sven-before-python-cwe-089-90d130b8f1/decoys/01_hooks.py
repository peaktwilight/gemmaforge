def get_output(command: List[str]) -> str:
    """
    Run a command and return raw output

    :param str command: the command to run
    :returns: the stdout output of the command
    """
    result = subprocess.run(command, stdout=subprocess.PIPE, check=True)
    return result.stdout.decode()
