def create_basename_core(basename):
    try:
        basename = basename.casefold()
    except Exception:
        basename = basename.lower()

    basename = re.sub(r'[ \./]', r'-', basename)
    basename = re.sub(r'<[^>]*>', r'', basename)
    basename = re.sub(r'[^a-z0-9\-]', r'', basename)
    basename = re.sub(r'\-\-', r'-', basename)
    basename = urllib.parse.quote_plus(basename)

    return basename
