def _get_settings(view):
    return {
        'linters': get_settings(view, 'anaconda_go_linters', []),
        'lint_test': get_settings(
            view, 'anaconda_go_lint_test', False),
        'exclude_regexps': get_settings(
            view, 'anaconda_go_exclude_regexps', []),
        'max_line_length': get_settings(
            view, 'anaconda_go_max_line_length', 120),
        'gocyclo_threshold': get_settings(
            view, 'anaconda_go_gocyclo_threshold', 10),
        'golint_min_confidence': get_settings(
            view, 'anaconda_go_golint_min_confidence', 0.80),
        'goconst_min_occurrences': get_settings(
            view, 'anaconda_go_goconst_min_occurrences', 3),
        'min_const_length': get_settings(
            view, 'anaconda_go_min_const_length', 3),
        'dupl_threshold': get_settings(
            view, 'anaconda_go_dupl_threshold', 50),
        'path': get_working_directory(view)
    }
