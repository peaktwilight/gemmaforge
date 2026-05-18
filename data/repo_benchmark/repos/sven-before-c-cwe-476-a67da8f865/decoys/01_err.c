http_error_t::make_body (int n, const str &si, const str &aux)
{
  strbuf b;
  str ldesc;
  const str sdesc = xss_escape (http_status.get_desc (n, &ldesc));
  b << "<html>\n"
    << " <head>\n"
    << "  <title>" << n << " " << sdesc << "</title>\n"
    << " </head>\n"
    << " <body>\n"
    << " <h1>Error " << n << " " << sdesc << "</h1><br><br>\n"
    ;
  if (n == HTTP_NOT_FOUND && aux) {
    b << "The file <tt>" << xss_escape (aux)
      << "</tt> was not found on this server.<br><br>\n\n";
  }
  b << "  <hr>\n"
    << "  <i>" << xss_escape (si) << "</i>\n"
    << " <br>\n"
    << " </body>\n"
    << "</html>\n"
    ;
  return b;
}
