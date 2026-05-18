rfbHandleAuthResult(rfbClient* client)
{
    uint32_t authResult=0;

    if (!ReadFromRFBServer(client, (char *)&authResult, 4)) return FALSE;

    authResult = rfbClientSwap32IfLE(authResult);

    switch (authResult) {
    case rfbVncAuthOK:
      rfbClientLog("VNC authentication succeeded\n");
      return TRUE;
      break;
    case rfbVncAuthFailed:
      if (client->major==3 && client->minor>7)
      {
        /* we have an error following */
        ReadReason(client);
        return FALSE;
      }
      rfbClientLog("VNC authentication failed\n");
      return FALSE;
    case rfbVncAuthTooMany:
      rfbClientLog("VNC authentication failed - too many tries\n");
      return FALSE;
    }

    rfbClientLog("Unknown VNC authentication result: %d\n",
                 (int)authResult);
    return FALSE;
}
