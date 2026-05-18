const char *enc_untrusted_inet_ntop(int af, const void *src, char *dst,
                                    socklen_t size) {
  if (!src || !dst) {
    errno = EFAULT;
    return nullptr;
  }
  size_t src_size = 0;
  if (af == AF_INET) {
    src_size = sizeof(struct in_addr);
  } else if (af == AF_INET6) {
    src_size = sizeof(struct in6_addr);
  } else {
    errno = EAFNOSUPPORT;
    return nullptr;
  }

  MessageWriter input;
  input.Push<int>(TokLinuxAfFamily(af));
  input.PushByReference(Extent{reinterpret_cast<const char *>(src), src_size});
  input.Push(size);
  MessageReader output;

  const auto status = NonSystemCallDispatcher(
      ::asylo::host_call::kInetNtopHandler, &input, &output);
  CheckStatusAndParamCount(status, output, "enc_untrusted_inet_ntop", 2);

  auto result = output.next();
  int klinux_errno = output.next<int>();
  if (result.empty()) {
    errno = FromkLinuxErrorNumber(klinux_errno);
    return nullptr;
  }

  memcpy(dst, result.data(),
         std::min(static_cast<size_t>(size),
                  static_cast<size_t>(INET6_ADDRSTRLEN)));
  return dst;
}
