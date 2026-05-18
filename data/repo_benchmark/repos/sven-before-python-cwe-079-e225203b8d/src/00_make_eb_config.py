def make_eb_config(application_name, default_region):
    # Capture our current directory
    UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
    # Create the jinja2 environment.
    # Notice the use of trim_blocks, which greatly helps control whitespace.
    j2_env = Environment(loader=FileSystemLoader(UTILS_DIR))
    return j2_env.get_template('templates/eb/config.yml').render(
        APPLICATION_NAME=application_name,
        DEFAULT_REGION=default_region
    )
