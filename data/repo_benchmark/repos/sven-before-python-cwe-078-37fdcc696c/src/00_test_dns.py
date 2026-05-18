@then(parsers.parse("the hostname '{hostname}' should be resolved"))
def resolve_hostname(busybox_pod, host, hostname):
        with host.sudo():
            # test dns resolve
            cmd_nslookup = ("kubectl --kubeconfig=/etc/kubernetes/admin.conf"
                            " exec -ti {0} nslookup {1}".format(
                                pod_name,
                                hostname))
            res = host.run(cmd_nslookup)
            assert res.rc == 0, "Cannot resolve {}".format(hostname)
