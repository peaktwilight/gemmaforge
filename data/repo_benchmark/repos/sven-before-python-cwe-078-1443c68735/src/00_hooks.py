def get_lines(command: str) -> List[str]:
    """
    Run a command and return lines of output

    :param str command: the command to run
    :returns: list of whitespace-stripped lines output by command
    """
    stdout = get_output(command)
    return [line.strip().decode() for line in stdout.splitlines()]
