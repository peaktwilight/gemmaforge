def get_title_from_youtube_url(url):
    try:
        output = str(subprocess.check_output(['youtube-dl', '--get-title', url, '--no-warnings'],
                                             stderr=subprocess.STDOUT)).strip()
    except subprocess.CalledProcessError as ex:
        output = str(ex.output).strip()
    except OSError as ex:
        output = 'youtube-dl not found: %s' % ex
    except Exception as ex:
        output = 'Something bad happened: %s' % ex
    return remove_commas_from_string(output)
