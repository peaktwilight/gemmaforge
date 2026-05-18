def test_settings_path_skip_issue_909(tmpdir):
    base_dir = tmpdir.mkdir('project')
    config_dir = base_dir.mkdir('conf')
    config_dir.join('.isort.cfg').write('[isort]\n'
                                        'skip =\n'
                                        '    file_to_be_skipped.py\n'
                                        'skip_glob =\n'
                                        '    *glob_skip*\n')

    base_dir.join('file_glob_skip.py').write('import os\n'
                                             '\n'
                                             'print("Hello World")\n'
                                             '\n'
                                             'import sys\n')
    base_dir.join('file_to_be_skipped.py').write('import os\n'
                                                 '\n'
                                                 'print("Hello World")'
                                                 '\n'
                                                 'import sys\n')

    test_run_directory = os.getcwd()
    os.chdir(str(base_dir))
    with pytest.raises(Exception):  # without the settings path provided: the command should not skip & identify errors
        check_output(['isort', '--check-only'])
    results = check_output(['isort', '--check-only', '--settings-path=conf/.isort.cfg'])
    os.chdir(str(test_run_directory))

    assert b'skipped 2' in results.lower()
