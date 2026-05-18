    def misc_file_checks(self):

        print_header("MISC FILE CHECKS")

        #
        # Check for recommended and mandatory files
        #

        filenames = ("manifest.json", "LICENSE", "README.md",
                     "scripts/install", "scripts/remove",
                     "scripts/upgrade",
                     "scripts/backup", "scripts/restore")
        non_mandatory = ("script/backup", "script/restore")

        for filename in filenames:
            if file_exists(self.path + "/" + filename):
                continue
            elif filename in non_mandatory:
                print_warning("Consider adding a file %s" % filename)
            else:
                print_error("File %s is mandatory" % filename)

        #
        # Deprecated php-fpm.ini thing
        #

        if file_exists(self.path + "/conf/php-fpm.ini"):
            print_warning(
                "Using a separate php-fpm.ini file is deprecated. "
                "Please merge your php-fpm directives directly in the pool file. "
                "(c.f. https://github.com/YunoHost-Apps/nextcloud_ynh/issues/138 )"
            )

        #
        # Analyze nginx conf
        # - Deprecated usage of 'add_header' in nginx conf
        # - Spot path traversal issue vulnerability
        #

        for filename in os.listdir(self.path + "/conf"):
            # Ignore subdirs or filename not containing nginx in the name
            if not os.path.isfile(self.path + "/conf/" + filename) or "nginx" not in filename:
                continue

            #
            # 'add_header' usage
            #
            content = open(self.path + "/conf/" + filename).read()
            if "location" in content and "add_header" in content:
                print_warning(
                    "Do not use 'add_header' in the nginx conf. Use 'more_set_headers' instead. "
                    "(See https://www.peterbe.com/plog/be-very-careful-with-your-add_header-in-nginx "
                    "and https://github.com/openresty/headers-more-nginx-module#more_set_headers )"
                )

            #
            # Path traversal issues
            #
            lines = open(self.path + "/conf/" + filename).readlines()
            lines = [line.strip() for line in lines if not line.strip().startswith("#")]
            # Let's find the first location line
            location_line = None
            path_traversal_vulnerable = False
            lines_iter = lines.__iter__()
            for line in lines_iter:
                if line.startswith("location"):
                    location_line = line
                    break
            # Look at the next lines for an 'alias' directive
            if location_line is not None:
                for line in lines_iter:
                    if line.startswith("location"):
                        # Entering a new location block ... abort here
                        # and assume there's no alias block later...
                        break
                    if line.startswith("alias"):
                        # We should definitely check for path traversal issue
                        # Does the location target ends with / ?
                        target = location_line.split()[-2]
                        if not target.endswith("/"):
                            path_traversal_vulnerable = True
                        break
            if path_traversal_vulnerable:
                print_warning(
                    "The nginx configuration appears vulnerable to path traversal as explained in "
                    "https://www.acunetix.com/vulnerabilities/web/path-traversal-via-misconfigured-nginx-alias/\n"
                    "To fix it, look at the first lines of the nginx conf of the example app : "
                    "https://github.com/YunoHost/example_ynh/blob/master/conf/nginx.conf"
                )
