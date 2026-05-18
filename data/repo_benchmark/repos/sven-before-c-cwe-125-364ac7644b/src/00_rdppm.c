start_input_ppm(j_compress_ptr cinfo, cjpeg_source_ptr sinfo)
{
  ppm_source_ptr source = (ppm_source_ptr)sinfo;
  int c;
  unsigned int w, h, maxval;
  boolean need_iobuffer, use_raw_buffer, need_rescale;

  if (getc(source->pub.input_file) != 'P')
    ERREXIT(cinfo, JERR_PPM_NOT);

  c = getc(source->pub.input_file); /* subformat discriminator character */

  /* detect unsupported variants (ie, PBM) before trying to read header */
  switch (c) {
  case '2':                     /* it's a text-format PGM file */
  case '3':                     /* it's a text-format PPM file */
  case '5':                     /* it's a raw-format PGM file */
  case '6':                     /* it's a raw-format PPM file */
    break;
  default:
    ERREXIT(cinfo, JERR_PPM_NOT);
    break;
  }

  /* fetch the remaining header info */
  w = read_pbm_integer(cinfo, source->pub.input_file, 65535);
  h = read_pbm_integer(cinfo, source->pub.input_file, 65535);
  maxval = read_pbm_integer(cinfo, source->pub.input_file, 65535);

  if (w <= 0 || h <= 0 || maxval <= 0) /* error check */
    ERREXIT(cinfo, JERR_PPM_NOT);

  cinfo->data_precision = BITS_IN_JSAMPLE; /* we always rescale data to this */
  cinfo->image_width = (JDIMENSION)w;
  cinfo->image_height = (JDIMENSION)h;
  source->maxval = maxval;

  /* initialize flags to most common settings */
  need_iobuffer = TRUE;         /* do we need an I/O buffer? */
  use_raw_buffer = FALSE;       /* do we map input buffer onto I/O buffer? */
  need_rescale = TRUE;          /* do we need a rescale array? */

  switch (c) {
  case '2':                     /* it's a text-format PGM file */
    if (cinfo->in_color_space == JCS_UNKNOWN)
      cinfo->in_color_space = JCS_GRAYSCALE;
    TRACEMS2(cinfo, 1, JTRC_PGM_TEXT, w, h);
    if (cinfo->in_color_space == JCS_GRAYSCALE)
      source->pub.get_pixel_rows = get_text_gray_row;
    else if (IsExtRGB(cinfo->in_color_space))
      source->pub.get_pixel_rows = get_text_gray_rgb_row;
    else if (cinfo->in_color_space == JCS_CMYK)
      source->pub.get_pixel_rows = get_text_gray_cmyk_row;
    else
      ERREXIT(cinfo, JERR_BAD_IN_COLORSPACE);
    need_iobuffer = FALSE;
    break;

  case '3':                     /* it's a text-format PPM file */
    if (cinfo->in_color_space == JCS_UNKNOWN)
      cinfo->in_color_space = JCS_EXT_RGB;
    TRACEMS2(cinfo, 1, JTRC_PPM_TEXT, w, h);
    if (IsExtRGB(cinfo->in_color_space))
      source->pub.get_pixel_rows = get_text_rgb_row;
    else if (cinfo->in_color_space == JCS_CMYK)
      source->pub.get_pixel_rows = get_text_rgb_cmyk_row;
    else
      ERREXIT(cinfo, JERR_BAD_IN_COLORSPACE);
    need_iobuffer = FALSE;
    break;

  case '5':                     /* it's a raw-format PGM file */
    if (cinfo->in_color_space == JCS_UNKNOWN)
      cinfo->in_color_space = JCS_GRAYSCALE;
    TRACEMS2(cinfo, 1, JTRC_PGM, w, h);
    if (maxval > 255) {
      source->pub.get_pixel_rows = get_word_gray_row;
    } else if (maxval == MAXJSAMPLE && sizeof(JSAMPLE) == sizeof(U_CHAR) &&
               cinfo->in_color_space == JCS_GRAYSCALE) {
      source->pub.get_pixel_rows = get_raw_row;
      use_raw_buffer = TRUE;
      need_rescale = FALSE;
    } else {
      if (cinfo->in_color_space == JCS_GRAYSCALE)
        source->pub.get_pixel_rows = get_scaled_gray_row;
      else if (IsExtRGB(cinfo->in_color_space))
        source->pub.get_pixel_rows = get_gray_rgb_row;
      else if (cinfo->in_color_space == JCS_CMYK)
        source->pub.get_pixel_rows = get_gray_cmyk_row;
      else
        ERREXIT(cinfo, JERR_BAD_IN_COLORSPACE);
    }
    break;

  case '6':                     /* it's a raw-format PPM file */
    if (cinfo->in_color_space == JCS_UNKNOWN)
      cinfo->in_color_space = JCS_EXT_RGB;
    TRACEMS2(cinfo, 1, JTRC_PPM, w, h);
    if (maxval > 255) {
      source->pub.get_pixel_rows = get_word_rgb_row;
    } else if (maxval == MAXJSAMPLE && sizeof(JSAMPLE) == sizeof(U_CHAR) &&
               (cinfo->in_color_space == JCS_EXT_RGB
#if RGB_RED == 0 && RGB_GREEN == 1 && RGB_BLUE == 2 && RGB_PIXELSIZE == 3
                || cinfo->in_color_space == JCS_RGB
#endif
               )) {
      source->pub.get_pixel_rows = get_raw_row;
      use_raw_buffer = TRUE;
      need_rescale = FALSE;
    } else {
      if (IsExtRGB(cinfo->in_color_space))
        source->pub.get_pixel_rows = get_rgb_row;
      else if (cinfo->in_color_space == JCS_CMYK)
        source->pub.get_pixel_rows = get_rgb_cmyk_row;
      else
        ERREXIT(cinfo, JERR_BAD_IN_COLORSPACE);
    }
    break;
  }

  if (IsExtRGB(cinfo->in_color_space))
    cinfo->input_components = rgb_pixelsize[cinfo->in_color_space];
  else if (cinfo->in_color_space == JCS_GRAYSCALE)
    cinfo->input_components = 1;
  else if (cinfo->in_color_space == JCS_CMYK)
    cinfo->input_components = 4;

  /* Allocate space for I/O buffer: 1 or 3 bytes or words/pixel. */
  if (need_iobuffer) {
    if (c == '6')
      source->buffer_width = (size_t)w * 3 *
        ((maxval <= 255) ? sizeof(U_CHAR) : (2 * sizeof(U_CHAR)));
    else
      source->buffer_width = (size_t)w *
        ((maxval <= 255) ? sizeof(U_CHAR) : (2 * sizeof(U_CHAR)));
    source->iobuffer = (U_CHAR *)
      (*cinfo->mem->alloc_small) ((j_common_ptr)cinfo, JPOOL_IMAGE,
                                  source->buffer_width);
  }

  /* Create compressor input buffer. */
  if (use_raw_buffer) {
    /* For unscaled raw-input case, we can just map it onto the I/O buffer. */
    /* Synthesize a JSAMPARRAY pointer structure */
    source->pixrow = (JSAMPROW)source->iobuffer;
    source->pub.buffer = &source->pixrow;
    source->pub.buffer_height = 1;
  } else {
    /* Need to translate anyway, so make a separate sample buffer. */
    source->pub.buffer = (*cinfo->mem->alloc_sarray)
      ((j_common_ptr)cinfo, JPOOL_IMAGE,
       (JDIMENSION)w * cinfo->input_components, (JDIMENSION)1);
    source->pub.buffer_height = 1;
  }

  /* Compute the rescaling array if required. */
  if (need_rescale) {
    long val, half_maxval;

    /* On 16-bit-int machines we have to be careful of maxval = 65535 */
    source->rescale = (JSAMPLE *)
      (*cinfo->mem->alloc_small) ((j_common_ptr)cinfo, JPOOL_IMAGE,
                                  (size_t)(((long)maxval + 1L) *
                                           sizeof(JSAMPLE)));
    half_maxval = maxval / 2;
    for (val = 0; val <= (long)maxval; val++) {
      /* The multiplication here must be done in 32 bits to avoid overflow */
      source->rescale[val] = (JSAMPLE)((val * MAXJSAMPLE + half_maxval) /
                                        maxval);
    }
  }
}
