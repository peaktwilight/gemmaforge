def test_skip_paths_issue_938(tmpdir):
    base_dir = tmpdir.mkdir('project')
    config_dir = base_dir.mkdir('conf')
    config_dir.join('.isort.cfg').write('[isort]\n'
                                        'line_length = 88\n'
                                        'multi_line_output = 4\n'
                                        'lines_after_imports = 2\n'
                                        'skip_glob =\n'
                                        '    migrations/**.py\n')
    base_dir.join('dont_skip.py').write('import os\n'
                                        '\n'
                                        'print("Hello World")'
                                        '\n'
                                        'import sys\n')

    migrations_dir = base_dir.mkdir('migrations')
    migrations_dir.join('file_glob_skip.py').write('import os\n'
                                                   '\n'
                                                   'print("Hello World")\n'
                                                   '\n'
                                                   'import sys\n')

    test_run_directory = os.getcwd()
    os.chdir(str(base_dir))
    results = check_output(['isort', 'dont_skip.py', 'migrations/file_glob_skip.py'])
    os.chdir(str(test_run_directory))

    assert b'skipped' not in results.lower()

    os.chdir(str(base_dir))
    results = check_output(['isort', '--filter-files', '--settings-path=conf/.isort.cfg', 'dont_skip.py', 'migrations/file_glob_skip.py'])
    os.chdir(str(test_run_directory))

    assert b'skipped 1' in results.lower()
