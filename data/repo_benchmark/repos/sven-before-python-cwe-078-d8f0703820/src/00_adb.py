    def tcp_forward(self, host_port, device_port):
        """Starts tcp forwarding.

        Args:
            host_port: Port number to use on the computer.
            device_port: Port number to use on the android device.
        """
        self.forward('tcp:%d tcp:%d' % (host_port, device_port))
