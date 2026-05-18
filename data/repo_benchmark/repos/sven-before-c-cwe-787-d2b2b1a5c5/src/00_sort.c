keycompare_mb (const struct line *a, const struct line *b)
{
  struct keyfield *key = keylist;

  /* For the first iteration only, the key positions have been
     precomputed for us. */
  char *texta = a->keybeg;
  char *textb = b->keybeg;
  char *lima = a->keylim;
  char *limb = b->keylim;

  size_t mblength_a, mblength_b;
  wchar_t wc_a, wc_b;
  mbstate_t state_a, state_b;

  int diff = 0;

  memset (&state_a, '\0', sizeof(mbstate_t));
  memset (&state_b, '\0', sizeof(mbstate_t));
  /* Ignore keys with start after end.  */
  if (a->keybeg - a->keylim > 0)
    return 0;


              /* Ignore and/or translate chars before comparing.  */
# define IGNORE_CHARS(NEW_LEN, LEN, TEXT, COPY, WC, MBLENGTH, STATE)        \
  do                                                                        \
    {                                                                        \
      wchar_t uwc;                                                        \
      char mbc[MB_LEN_MAX];                                                \
      mbstate_t state_wc;                                                \
                                                                        \
      for (NEW_LEN = i = 0; i < LEN;)                                        \
        {                                                                \
          mbstate_t state_bak;                                                \
                                                                        \
          state_bak = STATE;                                                \
          MBLENGTH = mbrtowc (&WC, TEXT + i, LEN - i, &STATE);                \
                                                                        \
          if (MBLENGTH == (size_t)-2 || MBLENGTH == (size_t)-1                \
              || MBLENGTH == 0)                                                \
            {                                                                \
              if (MBLENGTH == (size_t)-2 || MBLENGTH == (size_t)-1)        \
                STATE = state_bak;                                        \
              if (!ignore)                                                \
                COPY[NEW_LEN++] = TEXT[i];                                \
              i++;                                                         \
              continue;                                                        \
            }                                                                \
                                                                        \
          if (ignore)                                                        \
            {                                                                \
              if ((ignore == nonprinting && !iswprint (WC))                \
                   || (ignore == nondictionary                                \
                       && !iswalnum (WC) && !iswblank (WC)))                \
                {                                                        \
                  i += MBLENGTH;                                        \
                  continue;                                                \
                }                                                        \
            }                                                                \
                                                                        \
          if (translate)                                                \
            {                                                                \
                                                                        \
              uwc = towupper(WC);                                        \
              if (WC == uwc)                                                \
                {                                                        \
                  memcpy (mbc, TEXT + i, MBLENGTH);                        \
                  i += MBLENGTH;                                        \
                }                                                        \
              else                                                        \
                {                                                        \
                  i += MBLENGTH;                                        \
                  WC = uwc;                                                \
                  memset (&state_wc, '\0', sizeof (mbstate_t));                \
                                                                        \
                  MBLENGTH = wcrtomb (mbc, WC, &state_wc);                \
                  assert (MBLENGTH != (size_t)-1 && MBLENGTH != 0);        \
                }                                                        \
                                                                        \
              for (j = 0; j < MBLENGTH; j++)                                \
                COPY[NEW_LEN++] = mbc[j];                                \
            }                                                                \
          else                                                                \
            for (j = 0; j < MBLENGTH; j++)                                \
              COPY[NEW_LEN++] = TEXT[i++];                                \
        }                                                                \
      COPY[NEW_LEN] = '\0';                                                \
    }                                                                        \
  while (0)

      /* Actually compare the fields. */

  for (;;)
    {
      /* Find the lengths. */
      size_t lena = lima <= texta ? 0 : lima - texta;
      size_t lenb = limb <= textb ? 0 : limb - textb;

      char enda IF_LINT (= 0);
      char endb IF_LINT (= 0);

      char const *translate = key->translate;
      bool const *ignore = key->ignore;

      if (ignore || translate)
        {
          char *copy_a = (char *) xmalloc (lena + 1 + lenb + 1);
          char *copy_b = copy_a + lena + 1;
          size_t new_len_a, new_len_b;
          size_t i, j;

          IGNORE_CHARS (new_len_a, lena, texta, copy_a,
                        wc_a, mblength_a, state_a);
          IGNORE_CHARS (new_len_b, lenb, textb, copy_b,
                        wc_b, mblength_b, state_b);
          texta = copy_a; textb = copy_b;
          lena = new_len_a; lenb = new_len_b;
        }
      else
        {
          /* Use the keys in-place, temporarily null-terminated.  */
          enda = texta[lena]; texta[lena] = '\0';
          endb = textb[lenb]; textb[lenb] = '\0';
        }

      if (key->random)
        diff = compare_random (texta, lena, textb, lenb);
      else if (key->numeric | key->general_numeric | key->human_numeric)
        {
          char savea = *lima, saveb = *limb;

          *lima = *limb = '\0';
          diff = (key->numeric ? numcompare (texta, textb)
                  : key->general_numeric ? general_numcompare (texta, textb)
                  : human_numcompare (texta, textb));
          *lima = savea, *limb = saveb;
        }
      else if (key->version)
        diff = filevercmp (texta, textb);
      else if (key->month)
        diff = getmonth (texta, lena, NULL) - getmonth (textb, lenb, NULL);
      else if (lena == 0)
        diff = - NONZERO (lenb);
      else if (lenb == 0)
        diff = 1;
      else if (hard_LC_COLLATE && !folding)
        {
          diff = xmemcoll0 (texta, lena + 1, textb, lenb + 1);
        }
      else
        {
          diff = memcmp (texta, textb, MIN (lena, lenb));
          if (diff == 0)
            diff = lena < lenb ? -1 : lena != lenb;
        }

      if (ignore || translate)
        free (texta);
      else
        {
          texta[lena] = enda;
          textb[lenb] = endb;
        }

      if (diff)
        goto not_equal;

      key = key->next;
      if (! key)
        break;

      /* Find the beginning and limit of the next field.  */
      if (key->eword != -1)
        lima = limfield (a, key), limb = limfield (b, key);
      else
        lima = a->text + a->length - 1, limb = b->text + b->length - 1;

      if (key->sword != -1)
        texta = begfield (a, key), textb = begfield (b, key);
      else
        {
          texta = a->text, textb = b->text;
          if (key->skipsblanks)
            {
              while (texta < lima && ismbblank (texta, lima - texta, &mblength_a))
                texta += mblength_a;
              while (textb < limb && ismbblank (textb, limb - textb, &mblength_b))
                textb += mblength_b;
            }
        }
    }

not_equal:
  if (key && key->reverse)
    return -diff;
  else
    return diff;
}
