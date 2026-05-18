@then(parsers.parse("the hostname '{hostname}' should be resolved"))
def resolve_hostname(busybox_pod, host, hostname):
    with host.sudo():
        # test dns resolve
        result = host.run(
            "kubectl --kubeconfig=/etc/kubernetes/admin.conf "
            "exec -ti %s nslookup %s",
            busybox_pod,
            hostname,
        )

        assert result.rc == 0, "Cannot resolve {}".format(hostname)
