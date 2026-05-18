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
        # Deprecated usage of 'add_header' in nginx conf
        #

        for filename in os.listdir(self.path + "/conf"):
            if not os.path.isfile(self.path + "/conf/" + filename):
                continue
            content = open(self.path + "/conf/" + filename).read()
            if "location" in content and "add_header" in content:
                print_warning(
                    "Do not use 'add_header' in the nginx conf. Use 'more_set_headers' instead. "
                    "(See https://www.peterbe.com/plog/be-very-careful-with-your-add_header-in-nginx "
                    "and https://github.com/openresty/headers-more-nginx-module#more_set_headers )"
                )
