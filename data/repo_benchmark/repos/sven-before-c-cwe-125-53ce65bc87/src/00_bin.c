static int string_scan_range(RList *list, const ut8 *buf, int min,
			      const ut64 from, const ut64 to, int type) {
	ut8 tmp[R_STRING_SCAN_BUFFER_SIZE];
	ut64 str_start, needle = from;
	int count = 0, i, rc, runes;
	int str_type = R_STRING_TYPE_DETECT;

	if (type == -1) {
		type = R_STRING_TYPE_DETECT;
	}
	if (!buf || !min) {
		return -1;
	}
	while (needle < to) {
		rc = r_utf8_decode (buf + needle, to - needle, NULL);
		if (!rc) {
			needle++;
			continue;
		}

		if (type == R_STRING_TYPE_DETECT) {
			char *w = (char *)buf + needle + rc;
			if ((to - needle) > 4) {
				bool is_wide32 = needle + rc + 2 < to && !w[0] && !w[1] && !w[2] && w[3] && !w[4];
				if (is_wide32) {
					str_type = R_STRING_TYPE_WIDE32;
				} else {
					bool is_wide = needle + rc + 2 < to && !w[0] && w[1] && !w[2];
					str_type = is_wide? R_STRING_TYPE_WIDE: R_STRING_TYPE_ASCII;
				}
			} else {
				str_type = R_STRING_TYPE_ASCII;
			}
		} else {
			str_type = type;
		}


		runes = 0;
		str_start = needle;

		/* Eat a whole C string */
		for (rc = i = 0; i < sizeof (tmp) - 3 && needle < to; i += rc) {
			RRune r = {0};

			if (str_type == R_STRING_TYPE_WIDE32) {
				rc = r_utf32le_decode (buf + needle, to - needle, &r);
				if (rc) {
					rc = 4;
				}
			} else if (str_type == R_STRING_TYPE_WIDE) {
				rc = r_utf16le_decode (buf + needle, to - needle, &r);
				if (rc == 1) {
					rc = 2;
				}
			} else {
				rc = r_utf8_decode (buf + needle, to - needle, &r);
				if (rc > 1) {
					str_type = R_STRING_TYPE_UTF8;
				}
			}

			/* Invalid sequence detected */
			if (!rc) {
				needle++;
				break;
			}

			needle += rc;

			if (r_isprint (r)) {
				if (str_type == R_STRING_TYPE_WIDE32) {
					if (r == 0xff) {
						r = 0;
					}
				}
				rc = r_utf8_encode (&tmp[i], r);
				runes++;
				/* Print the escape code */
			} else if (r && r < 0x100 && strchr ("\b\v\f\n\r\t\a\e", (char)r)) {
				if ((i + 32) < sizeof (tmp) && r < 28) {
					tmp[i + 0] = '\\';
					tmp[i + 1] = "       abtnvfr             e"[r];
				} else {
					// string too long
					break;
				}
				rc = 2;
				runes++;
			} else {
				/* \0 marks the end of C-strings */
				break;
			}
		}

		tmp[i++] = '\0';

		if (runes >= min) {
			if (str_type == R_STRING_TYPE_ASCII) {
				// reduce false positives
				int j;
				for (j = 0; j < i; j++) {
					char ch = tmp[j];
					if (ch != '\n' && ch != '\r' && ch != '\t') {
						if (!IS_PRINTABLE (tmp[j])) {
							continue;
						}
					}
				}
			}
			if (list) {
				RBinString *new = R_NEW0 (RBinString);
				if (!new) {
					break;
				}
				new->type = str_type;
				new->length = runes;
				new->size = needle - str_start;
				new->ordinal = count++;
				// TODO: move into adjust_offset
				switch (str_type) {
				case R_STRING_TYPE_WIDE:
					{
						const ut8 *p = buf  + str_start - 2;
						if (p[0] == 0xff && p[1] == 0xfe) {
							str_start -= 2; // \xff\xfe
						}
					}
					break;
				case R_STRING_TYPE_WIDE32:
					{
						const ut8 *p = buf  + str_start - 4;
						if (p[0] == 0xff && p[1] == 0xfe) {
							str_start -= 4; // \xff\xfe\x00\x00
						}
					}
					break;
				}
				new->paddr = new->vaddr = str_start;
				new->string = r_str_ndup ((const char *)tmp, i);
				r_list_append (list, new);
			} else {
				// DUMP TO STDOUT. raw dumping for rabin2 -zzz
				printf ("0x%08" PFMT64x " %s\n", str_start, tmp);
			}
		}
	}
	return count;
}
