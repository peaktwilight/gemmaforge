    def _run_ssh(self, cmd_list, check_exit=True, attempts=1):
        utils.check_ssh_injection(cmd_list)
        command = ' '. join(cmd_list)

        if not self.sshpool:
            self.sshpool = utils.SSHPool(self.config.san_ip,
                                         self.config.san_ssh_port,
                                         self.config.ssh_conn_timeout,
                                         self.config.san_login,
                                         password=self.config.san_password,
                                         privatekey=
                                         self.config.san_private_key,
                                         min_size=
                                         self.config.ssh_min_pool_conn,
                                         max_size=
                                         self.config.ssh_max_pool_conn)
        try:
            total_attempts = attempts
            with self.sshpool.item() as ssh:
                while attempts > 0:
                    attempts -= 1
                    try:
                        return self._ssh_execute(ssh, command,
                                                 check_exit_code=check_exit)
                    except Exception as e:
                        LOG.error(e)
                        greenthread.sleep(randint(20, 500) / 100.0)
                msg = (_("SSH Command failed after '%(total_attempts)r' "
                         "attempts : '%(command)s'") %
                       {'total_attempts': total_attempts, 'command': command})
                raise paramiko.SSHException(msg)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error(_("Error running ssh command: %s") % command)
