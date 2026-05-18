def git_hook(strict=False, modify=False):
    """
    Git pre-commit hook to check staged files for isort errors

    :param bool strict - if True, return number of errors on exit,
        causing the hook to fail. If False, return zero so it will
        just act as a warning.
    :param bool modify - if True, fix the sources if they are not
        sorted properly. If False, only report result without
        modifying anything.

    :return number of errors if in strict mode, 0 otherwise.
    """

    # Get list of files modified and staged
    diff_cmd = "git diff-index --cached --name-only --diff-filter=ACMRTUXB HEAD"
    files_modified = get_lines(diff_cmd)

    errors = 0
    for filename in files_modified:
        if filename.endswith('.py'):
            # Get the staged contents of the file
            staged_cmd = "git show :%s" % filename
            staged_contents = get_output(staged_cmd)

            sort = SortImports(
                file_path=filename,
                file_contents=staged_contents.decode(),
                check=True
            )

            if sort.incorrectly_sorted:
                errors += 1
                if modify:
                    SortImports(
                        file_path=filename,
                        file_contents=staged_contents.decode(),
                        check=False,
                    )

    return errors if strict else 0
