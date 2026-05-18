def _call_external_zip(base_dir, zip_filename, verbose, dry_run, logger):
    # XXX see if we want to keep an external call here
    if verbose:
        zipoptions = "-r"
    else:
        zipoptions = "-rq"
    cmd = ["zip", zipoptions, zip_filename, base_dir]
    if logger is not None:
        logger.info(' '.join(cmd))
    if dry_run:
        return
    import subprocess
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        # XXX really should distinguish between "couldn't find
        # external 'zip' command" and "zip failed".
        raise ExecError, \
            ("unable to create zip file '%s': "
            "could neither import the 'zipfile' module nor "
            "find a standalone zip utility") % zip_filename
