void Logger::addPeer(const QString &ip, bool blocked, const QString &reason)
{
    QWriteLocker locker(&lock);

    Log::Peer temp = { peerCounter++, QDateTime::currentMSecsSinceEpoch(), ip, blocked, reason };
    m_peers.push_back(temp);

    if (m_peers.size() >= MAX_LOG_MESSAGES)
        m_peers.pop_front();

    emit newLogPeer(temp);
}
