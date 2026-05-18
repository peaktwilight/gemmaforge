    def write_section(self, section_name, section_data):
        self.write_line("")
        self.write_line("define %s {" % section_name)
        sorted_keys = section_data.keys()
        sorted_keys.sort()
        for key in sorted_keys:
            value = self.value_to_icinga(section_data[key])
            icinga_line = "%s%-45s%s" % (self.indent, key, value)

            if "\n" in icinga_line or "}" in icinga_line:
                msg = "Found forbidden newline or '}' character in section %r."
                raise Exception(msg % section_name)

            self.icinga_lines.append(icinga_line)
        self.write_line("}")
