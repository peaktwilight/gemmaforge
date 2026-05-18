InitialiseRFBConnection(rfbClient* client)
{
  rfbProtocolVersionMsg pv;
  int major,minor;
  uint32_t authScheme;
  uint32_t subAuthScheme;
  rfbClientInitMsg ci;

  /* if the connection is immediately closed, don't report anything, so
       that pmw's monitor can make test connections */

  if (client->listenSpecified)
    errorMessageOnReadFailure = FALSE;

  if (!ReadFromRFBServer(client, pv, sz_rfbProtocolVersionMsg)) return FALSE;
  pv[sz_rfbProtocolVersionMsg]=0;

  errorMessageOnReadFailure = TRUE;

  pv[sz_rfbProtocolVersionMsg] = 0;

  if (sscanf(pv,rfbProtocolVersionFormat,&major,&minor) != 2) {
    rfbClientLog("Not a valid VNC server (%s)\n",pv);
    return FALSE;
  }


  DefaultSupportedMessages(client);
  client->major = major;
  client->minor = minor;

  /* fall back to viewer supported version */
  if ((major==rfbProtocolMajorVersion) && (minor>rfbProtocolMinorVersion))
    client->minor = rfbProtocolMinorVersion;

  /* UltraVNC uses minor codes 4 and 6 for the server */
  if (major==3 && (minor==4 || minor==6)) {
      rfbClientLog("UltraVNC server detected, enabling UltraVNC specific messages\n",pv);
      DefaultSupportedMessagesUltraVNC(client);
  }

  /* UltraVNC Single Click uses minor codes 14 and 16 for the server */
  if (major==3 && (minor==14 || minor==16)) {
     minor = minor - 10;
     client->minor = minor;
     rfbClientLog("UltraVNC Single Click server detected, enabling UltraVNC specific messages\n",pv);
     DefaultSupportedMessagesUltraVNC(client);
  }

  /* TightVNC uses minor codes 5 for the server */
  if (major==3 && minor==5) {
      rfbClientLog("TightVNC server detected, enabling TightVNC specific messages\n",pv);
      DefaultSupportedMessagesTightVNC(client);
  }

  /* we do not support > RFB3.8 */
  if ((major==3 && minor>8) || major>3)
  {
    client->major=3;
    client->minor=8;
  }

  rfbClientLog("VNC server supports protocol version %d.%d (viewer %d.%d)\n",
	  major, minor, rfbProtocolMajorVersion, rfbProtocolMinorVersion);

  sprintf(pv,rfbProtocolVersionFormat,client->major,client->minor);

  if (!WriteToRFBServer(client, pv, sz_rfbProtocolVersionMsg)) return FALSE;


  /* 3.7 and onwards sends a # of security types first */
  if (client->major==3 && client->minor > 6)
  {
    if (!ReadSupportedSecurityType(client, &authScheme, FALSE)) return FALSE;
  }
  else
  {
    if (!ReadFromRFBServer(client, (char *)&authScheme, 4)) return FALSE;
    authScheme = rfbClientSwap32IfLE(authScheme);
  }
  
  rfbClientLog("Selected Security Scheme %d\n", authScheme);
  client->authScheme = authScheme;
  
  switch (authScheme) {

  case rfbConnFailed:
    ReadReason(client);
    return FALSE;

  case rfbNoAuth:
    rfbClientLog("No authentication needed\n");

    /* 3.8 and upwards sends a Security Result for rfbNoAuth */
    if ((client->major==3 && client->minor > 7) || client->major>3)
        if (!rfbHandleAuthResult(client)) return FALSE;        

    break;

  case rfbVncAuth:
    if (!HandleVncAuth(client)) return FALSE;
    break;

#ifdef LIBVNCSERVER_HAVE_SASL
  case rfbSASL:
    if (!HandleSASLAuth(client)) return FALSE;
    break;
#endif /* LIBVNCSERVER_HAVE_SASL */

  case rfbMSLogon:
    if (!HandleMSLogonAuth(client)) return FALSE;
    break;

  case rfbARD:
#ifndef LIBVNCSERVER_WITH_CLIENT_GCRYPT
    rfbClientLog("GCrypt support was not compiled in\n");
    return FALSE;
#else
    if (!HandleARDAuth(client)) return FALSE;
#endif
    break;

  case rfbTLS:
    if (!HandleAnonTLSAuth(client)) return FALSE;
    /* After the TLS session is established, sub auth types are expected.
     * Note that all following reading/writing are through the TLS session from here.
     */
    if (!ReadSupportedSecurityType(client, &subAuthScheme, TRUE)) return FALSE;
    client->subAuthScheme = subAuthScheme;

    switch (subAuthScheme) {

      case rfbConnFailed:
        ReadReason(client);
        return FALSE;

      case rfbNoAuth:
        rfbClientLog("No sub authentication needed\n");
        /* 3.8 and upwards sends a Security Result for rfbNoAuth */
        if ((client->major==3 && client->minor > 7) || client->major>3)
            if (!rfbHandleAuthResult(client)) return FALSE;
        break;

      case rfbVncAuth:
        if (!HandleVncAuth(client)) return FALSE;
        break;

#ifdef LIBVNCSERVER_HAVE_SASL
      case rfbSASL:
        if (!HandleSASLAuth(client)) return FALSE;
        break;
#endif /* LIBVNCSERVER_HAVE_SASL */

      default:
        rfbClientLog("Unknown sub authentication scheme from VNC server: %d\n",
            (int)subAuthScheme);
        return FALSE;
    }

    break;

  case rfbVeNCrypt:
    if (!HandleVeNCryptAuth(client)) return FALSE;

    switch (client->subAuthScheme) {

      case rfbVeNCryptTLSNone:
      case rfbVeNCryptX509None:
        rfbClientLog("No sub authentication needed\n");
        if (!rfbHandleAuthResult(client)) return FALSE;
        break;

      case rfbVeNCryptTLSVNC:
      case rfbVeNCryptX509VNC:
        if (!HandleVncAuth(client)) return FALSE;
        break;

      case rfbVeNCryptTLSPlain:
      case rfbVeNCryptX509Plain:
        if (!HandlePlainAuth(client)) return FALSE;
        break;

#ifdef LIBVNCSERVER_HAVE_SASL
      case rfbVeNCryptX509SASL:
      case rfbVeNCryptTLSSASL:
        if (!HandleSASLAuth(client)) return FALSE;
        break;
#endif /* LIBVNCSERVER_HAVE_SASL */

      default:
        rfbClientLog("Unknown sub authentication scheme from VNC server: %d\n",
            client->subAuthScheme);
        return FALSE;
    }

    break;

  default:
    {
      rfbBool authHandled=FALSE;
      rfbClientProtocolExtension* e;
      for (e = rfbClientExtensions; e; e = e->next) {
        uint32_t const* secType;
        if (!e->handleAuthentication) continue;
        for (secType = e->securityTypes; secType && *secType; secType++) {
          if (authScheme==*secType) {
            if (!e->handleAuthentication(client, authScheme)) return FALSE;
            if (!rfbHandleAuthResult(client)) return FALSE;
            authHandled=TRUE;
          }
        }
      }
      if (authHandled) break;
    }
    rfbClientLog("Unknown authentication scheme from VNC server: %d\n",
	    (int)authScheme);
    return FALSE;
  }

  ci.shared = (client->appData.shareDesktop ? 1 : 0);

  if (!WriteToRFBServer(client,  (char *)&ci, sz_rfbClientInitMsg)) return FALSE;

  if (!ReadFromRFBServer(client, (char *)&client->si, sz_rfbServerInitMsg)) return FALSE;

  client->si.framebufferWidth = rfbClientSwap16IfLE(client->si.framebufferWidth);
  client->si.framebufferHeight = rfbClientSwap16IfLE(client->si.framebufferHeight);
  client->si.format.redMax = rfbClientSwap16IfLE(client->si.format.redMax);
  client->si.format.greenMax = rfbClientSwap16IfLE(client->si.format.greenMax);
  client->si.format.blueMax = rfbClientSwap16IfLE(client->si.format.blueMax);
  client->si.nameLength = rfbClientSwap32IfLE(client->si.nameLength);

  if (client->si.nameLength > 1<<20) {
      rfbClientErr("Too big desktop name length sent by server: %u B > 1 MB\n", (unsigned int)client->si.nameLength);
      return FALSE;
  }

  client->desktopName = malloc(client->si.nameLength + 1);
  if (!client->desktopName) {
    rfbClientLog("Error allocating memory for desktop name, %lu bytes\n",
            (unsigned long)client->si.nameLength);
    return FALSE;
  }

  if (!ReadFromRFBServer(client, client->desktopName, client->si.nameLength)) return FALSE;

  client->desktopName[client->si.nameLength] = 0;

  rfbClientLog("Desktop name \"%s\"\n",client->desktopName);

  rfbClientLog("Connected to VNC server, using protocol version %d.%d\n",
	  client->major, client->minor);

  rfbClientLog("VNC server default format:\n");
  PrintPixelFormat(&client->si.format);

  return TRUE;
}
