  static bool TryParse(const char* inp, int length,
                       TypedValue* buf, Variant& out,
                       JSONContainerType container_type, bool is_tsimplejson) {
    SimpleParser parser(inp, length, buf, container_type, is_tsimplejson);
    bool ok = parser.parseValue();
    parser.skipSpace();
    if (!ok || parser.p != inp + length) {
      // Unsupported, malformed, or trailing garbage. Release entire stack.
      tvDecRefRange(buf, parser.top);
      return false;
    }
    out = Variant::attach(*--parser.top);
    return true;
  }
