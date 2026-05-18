static void core_anal_bytes(RCore *core, const ut8 *buf, int len, int nops, int fmt) {
	int stacksize = r_config_get_i (core->config, "esil.stack.depth");
	bool iotrap = r_config_get_i (core->config, "esil.iotrap");
	bool romem = r_config_get_i (core->config, "esil.romem");
	bool stats = r_config_get_i (core->config, "esil.stats");
	bool be = core->print->big_endian;
	bool use_color = core->print->flags & R_PRINT_FLAGS_COLOR;
	core->parser->relsub = r_config_get_i (core->config, "asm.relsub");
	int ret, i, j, idx, size;
	const char *color = "";
	const char *esilstr;
	const char *opexstr;
	RAnalHint *hint;
	RAnalEsil *esil = NULL;
	RAsmOp asmop;
	RAnalOp op = {0};
	ut64 addr;
	bool isFirst = true;
	unsigned int addrsize = r_config_get_i (core->config, "esil.addr.size");
	int totalsize = 0;

	// Variables required for setting up ESIL to REIL conversion
	if (use_color) {
		color = core->cons->pal.label;
	}
	switch (fmt) {
	case 'j':
		r_cons_printf ("[");
		break;
	case 'r':
		// Setup for ESIL to REIL conversion
		esil = r_anal_esil_new (stacksize, iotrap, addrsize);
		if (!esil) {
			return;
		}
		r_anal_esil_to_reil_setup (esil, core->anal, romem, stats);
		r_anal_esil_set_pc (esil, core->offset);
		break;
	}
	for (i = idx = ret = 0; idx < len && (!nops || (nops && i < nops)); i++, idx += ret) {
		addr = core->offset + idx;
		// TODO: use more anal hints
		hint = r_anal_hint_get (core->anal, addr);
		r_asm_set_pc (core->assembler, addr);
		(void)r_asm_disassemble (core->assembler, &asmop, buf + idx, len - idx);
		ret = r_anal_op (core->anal, &op, core->offset + idx, buf + idx, len - idx, R_ANAL_OP_MASK_ESIL);
		esilstr = R_STRBUF_SAFEGET (&op.esil);
		opexstr = R_STRBUF_SAFEGET (&op.opex);
		char *mnem = strdup (r_asm_op_get_asm (&asmop));
		char *sp = strchr (mnem, ' ');
		if (sp) {
			*sp = 0;
			if (op.prefix) {
				char *arg = strdup (sp + 1);
				char *sp = strchr (arg, ' ');
				if (sp) {
					*sp = 0;
				}
				free (mnem);
				mnem = arg;
			}
		}
		if (ret < 1 && fmt != 'd') {
			eprintf ("Oops at 0x%08" PFMT64x " (", core->offset + idx);
			for (i = idx, j = 0; i < core->blocksize && j < 3; ++i, ++j) {
				eprintf ("%02x ", buf[i]);
			}
			eprintf ("...)\n");
			free (mnem);
			break;
		}
		size = (hint && hint->size)? hint->size: op.size;
		if (fmt == 'd') {
			char *opname = strdup (r_asm_op_get_asm (&asmop));
			if (opname) {
				r_str_split (opname, ' ');
				char *d = r_asm_describe (core->assembler, opname);
				if (d && *d) {
					r_cons_printf ("%s: %s\n", opname, d);
					free (d);
				} else {
					eprintf ("Unknown opcode\n");
				}
				free (opname);
			}
		} else if (fmt == 'e') {
			if (*esilstr) {
				if (use_color) {
					r_cons_printf ("%s0x%" PFMT64x Color_RESET " %s\n", color, core->offset + idx, esilstr);
				} else {
					r_cons_printf ("0x%" PFMT64x " %s\n", core->offset + idx, esilstr);
				}
			}
		} else if (fmt == 's') {
			totalsize += op.size;
		} else if (fmt == 'r') {
			if (*esilstr) {
				if (use_color) {
					r_cons_printf ("%s0x%" PFMT64x Color_RESET "\n", color, core->offset + idx);
				} else {
					r_cons_printf ("0x%" PFMT64x "\n", core->offset + idx);
				}
				r_anal_esil_parse (esil, esilstr);
				r_anal_esil_dumpstack (esil);
				r_anal_esil_stack_free (esil);
			}
		} else if (fmt == 'j') {
			if (isFirst) {
				isFirst = false;
			} else {
				r_cons_print (",");
			}
			r_cons_printf ("{\"opcode\":\"%s\",", r_asm_op_get_asm (&asmop));
			{
				char strsub[128] = { 0 };
				// pc+33
				r_parse_varsub (core->parser, NULL,
					core->offset + idx,
					asmop.size, r_asm_op_get_asm (&asmop),
					strsub, sizeof (strsub));
				{
					ut64 killme = UT64_MAX;
					if (r_io_read_i (core->io, op.ptr, &killme, op.refptr, be)) {
						core->parser->relsub_addr = killme;
					}
				}
				// 0x33->sym.xx
				char *p = strdup (strsub);
				if (p) {
					r_parse_filter (core->parser, addr, core->flags, p,
							strsub, sizeof (strsub), be);
					free (p);
				}
				r_cons_printf ("\"disasm\":\"%s\",", strsub);
			}
			r_cons_printf ("\"mnemonic\":\"%s\",", mnem);
			if (hint && hint->opcode) {
				r_cons_printf ("\"ophint\":\"%s\",", hint->opcode);
			}
			r_cons_printf ("\"sign\":%s,", r_str_bool (op.sign));
			r_cons_printf ("\"prefix\":%" PFMT64u ",", op.prefix);
			r_cons_printf ("\"id\":%d,", op.id);
			if (opexstr && *opexstr) {
				r_cons_printf ("\"opex\":%s,", opexstr);
			}
			r_cons_printf ("\"addr\":%" PFMT64u ",", core->offset + idx);
			r_cons_printf ("\"bytes\":\"");
			for (j = 0; j < size; j++) {
				r_cons_printf ("%02x", buf[j + idx]);
			}
			r_cons_printf ("\",");
			if (op.val != UT64_MAX) {
				r_cons_printf ("\"val\": %" PFMT64u ",", op.val);
			}
			if (op.ptr != UT64_MAX) {
				r_cons_printf ("\"ptr\": %" PFMT64u ",", op.ptr);
			}
			r_cons_printf ("\"size\": %d,", size);
			r_cons_printf ("\"type\": \"%s\",",
				r_anal_optype_to_string (op.type));
			if (op.reg) {
				r_cons_printf ("\"reg\": \"%s\",", op.reg);
			}
			if (op.ireg) {
				r_cons_printf ("\"ireg\": \"%s\",", op.ireg);
			}
			if (op.scale) {
				r_cons_printf ("\"scale\":%d,", op.scale);
			}
			if (hint && hint->esil) {
				r_cons_printf ("\"esil\": \"%s\",", hint->esil);
			} else if (*esilstr) {
				r_cons_printf ("\"esil\": \"%s\",", esilstr);
			}
			if (hint && hint->jump != UT64_MAX) {
				op.jump = hint->jump;
			}
			if (op.jump != UT64_MAX) {
				r_cons_printf ("\"jump\":%" PFMT64u ",", op.jump);
			}
			if (hint && hint->fail != UT64_MAX) {
				op.fail = hint->fail;
			}
			if (op.refptr != -1) {
				r_cons_printf ("\"refptr\":%d,", op.refptr);
			}
			if (op.fail != UT64_MAX) {
				r_cons_printf ("\"fail\":%" PFMT64u ",", op.fail);
			}
			r_cons_printf ("\"cycles\":%d,", op.cycles);
			if (op.failcycles) {
				r_cons_printf ("\"failcycles\":%d,", op.failcycles);
			}
			r_cons_printf ("\"delay\":%d,", op.delay);
			{
				const char *p = r_anal_stackop_tostring (op.stackop);
				if (p && *p && strcmp (p, "null"))
					r_cons_printf ("\"stack\":\"%s\",", p);
			}
			if (op.stackptr) {
				r_cons_printf ("\"stackptr\":%d,", op.stackptr);
			}
			{
				const char *arg = (op.type & R_ANAL_OP_TYPE_COND)
					? r_anal_cond_tostring (op.cond): NULL;
				if (arg) {
					r_cons_printf ("\"cond\":\"%s\",", arg);
				}
			}
			r_cons_printf ("\"family\":\"%s\"}", r_anal_op_family_to_string (op.family));
		} else {
#define printline(k, fmt, arg)\
	{ \
		if (use_color)\
			r_cons_printf ("%s%s: " Color_RESET, color, k);\
		else\
			r_cons_printf ("%s: ", k);\
		if (fmt) r_cons_printf (fmt, arg);\
	}
			printline ("address", "0x%" PFMT64x "\n", core->offset + idx);
			printline ("opcode", "%s\n", r_asm_op_get_asm (&asmop));
			printline ("mnemonic", "%s\n", mnem);
			if (hint) {
				if (hint->opcode) {
					printline ("ophint", "%s\n", hint->opcode);
				}
#if 0
				// addr should not override core->offset + idx.. its silly
				if (hint->addr != UT64_MAX) {
					printline ("addr", "0x%08" PFMT64x "\n", (hint->addr + idx));
				}
#endif
			}
			printline ("prefix", "%" PFMT64u "\n", op.prefix);
			printline ("id", "%d\n", op.id);
#if 0
// no opex here to avoid lot of tests broken..and having json in here is not much useful imho
			if (opexstr && *opexstr) {
				printline ("opex", "%s\n", opexstr);
			}
#endif
			printline ("bytes", NULL, 0);
			int minsz = R_MIN (len, size);
			minsz = R_MAX (minsz, 0);
			for (j = 0; j < minsz; j++) {
				ut8 ch = ((j + idx - 1) > minsz)? 0xff: buf[j + idx];
				r_cons_printf ("%02x", ch);
			}
			r_cons_newline ();
			if (op.val != UT64_MAX) {
				printline ("val", "0x%08" PFMT64x "\n", op.val);
			}
			if (op.ptr != UT64_MAX) {
				printline ("ptr", "0x%08" PFMT64x "\n", op.ptr);
			}
			if (op.refptr != -1) {
				printline ("refptr", "%d\n", op.refptr);
			}
			printline ("size", "%d\n", size);
			printline ("sign", "%s\n", r_str_bool (op.sign));
			printline ("type", "%s\n", r_anal_optype_to_string (op.type));
			printline ("cycles", "%d\n", op.cycles);
			if (op.failcycles) {
				printline ("failcycles", "%d\n", op.failcycles);
			}
			{
				const char *t2 = r_anal_optype_to_string (op.type2);
				if (t2 && strcmp (t2, "null")) {
					printline ("type2", "%s\n", t2);
				}
			}
			if (op.reg) {
				printline ("reg", "%s\n", op.reg);
			}
			if (op.ireg) {
				printline ("ireg", "%s\n", op.ireg);
			}
			if (op.scale) {
				printline ("scale", "%d\n", op.scale);
			}
			if (hint && hint->esil) {
				printline ("esil", "%s\n", hint->esil);
			} else if (*esilstr) {
				printline ("esil", "%s\n", esilstr);
			}
			if (hint && hint->jump != UT64_MAX) {
				op.jump = hint->jump;
			}
			if (op.jump != UT64_MAX) {
				printline ("jump", "0x%08" PFMT64x "\n", op.jump);
			}
			if (op.direction != 0) {
				const char * dir = op.direction == 1 ? "read"
					: op.direction == 2 ? "write"
					: op.direction == 4 ? "exec"
					: op.direction == 8 ? "ref": "none";
				printline ("direction", "%s\n", dir);
			}
			if (hint && hint->fail != UT64_MAX) {
				op.fail = hint->fail;
			}
			if (op.fail != UT64_MAX) {
				printline ("fail", "0x%08" PFMT64x "\n", op.fail);
			}
			if (op.delay) {
				printline ("delay", "%d\n", op.delay);
			}
			printline ("stack", "%s\n", r_anal_stackop_tostring (op.stackop));
			{
				const char *arg = (op.type & R_ANAL_OP_TYPE_COND)?  r_anal_cond_tostring (op.cond): NULL;
				if (arg) {
					printline ("cond", "%s\n", arg);
				}
			}
			printline ("family", "%s\n", r_anal_op_family_to_string (op.family));
			printline ("stackop", "%s\n", r_anal_stackop_tostring (op.stackop));
			if (op.stackptr) {
				printline ("stackptr", "%"PFMT64u"\n", op.stackptr);
			}
		}
		//r_cons_printf ("false: 0x%08"PFMT64x"\n", core->offset+idx);
		//free (hint);
		free (mnem);
		r_anal_hint_free (hint);
		r_anal_op_fini (&op);
	}
	r_anal_op_fini (&op);
	if (fmt == 'j') {
		r_cons_printf ("]");
		r_cons_newline ();
	} else if (fmt == 's') {
		r_cons_printf ("%d\n", totalsize);
	}
	r_anal_esil_free (esil);
}
