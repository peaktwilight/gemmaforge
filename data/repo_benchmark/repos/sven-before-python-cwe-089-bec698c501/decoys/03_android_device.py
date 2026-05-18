    def take_bug_report(self, test_name, begin_time):
        """Takes a bug report on the device and stores it in a file.

        Args:
            test_name: Name of the test case that triggered this bug report.
            begin_time: Logline format timestamp taken when the test started.
        """
        new_br = True
        try:
            stdout = self.adb.shell('bugreportz -v').decode('utf-8')
            # This check is necessary for builds before N, where adb shell's ret
            # code and stderr are not propagated properly.
            if 'not found' in stdout:
                new_br = False
        except adb.AdbError:
            new_br = False
        br_path = os.path.join(self.log_path, 'BugReports')
        utils.create_dir(br_path)
        base_name = ',%s,%s.txt' % (begin_time, self.serial)
        if new_br:
            base_name = base_name.replace('.txt', '.zip')
        test_name_len = utils.MAX_FILENAME_LEN - len(base_name)
        out_name = test_name[:test_name_len] + base_name
        full_out_path = os.path.join(br_path, out_name.replace(' ', r'\ '))
        # in case device restarted, wait for adb interface to return
        self.wait_for_boot_completion()
        self.log.info('Taking bugreport for %s.', test_name)
        if new_br:
            out = self.adb.shell('bugreportz').decode('utf-8')
            if not out.startswith('OK'):
                raise DeviceError(self, 'Failed to take bugreport: %s' % out)
            br_out_path = out.split(':')[1].strip()
            self.adb.pull([br_out_path, full_out_path])
        else:
            # shell=True as this command redirects the stdout to a local file
            # using shell redirection.
            self.adb.bugreport(' > %s' % full_out_path, shell=True)
        self.log.info('Bugreport for %s taken at %s.', test_name,
                      full_out_path)
