def new_goal():
    """
    new goal
    """

    goals_dir_check()

    goal_name_not_ok = True

    click.echo(chalk.blue('Input a single-word name of the goal:'))
    while goal_name_not_ok:
        goal_name = input().strip()
        if goal_name.isalnum():
            goal_name_not_ok = False
        else:
            click.echo(chalk.red('Only alphanumeric characters can be used! Please input the goal name:'))

    if goal_name_exists(goal_name):
        click.echo(chalk.red(
            'A goal with this name already exists. Please type "yoda goals view" to see a list of existing goals'))
    else:
        click.echo(chalk.blue('Input description of the goal:'))
        text = input().strip()

        click.echo(chalk.blue('Input due date for the goal (YYYY-MM-DD):'))
        incorrect_date_format = True
        while incorrect_date_format:
            deadline = input().strip()
            try:
                date_str = datetime.datetime.strptime(deadline, '%Y-%m-%d').strftime('%Y-%m-%d')
                if date_str != deadline:
                    raise ValueError
                incorrect_date_format = False
            except ValueError:
                click.echo(chalk.red("Incorrect data format, should be YYYY-MM-DD. Please repeat:"))

        if os.path.isfile(GOALS_CONFIG_FILE_PATH):
            setup_data = dict(
                name=goal_name,
                text=text,
                deadline=deadline,
                status=0
            )
            append_data_into_file(setup_data, GOALS_CONFIG_FILE_PATH)
        else:
            setup_data = dict(
                entries=[
                    dict(
                        name=goal_name,
                        text=text,
                        deadline=deadline,
                        status=0
                    )
                ]
            )
            input_data(setup_data, GOALS_CONFIG_FILE_PATH)

        input_data(dict(entries=[]), get_goal_file_path(goal_name))
