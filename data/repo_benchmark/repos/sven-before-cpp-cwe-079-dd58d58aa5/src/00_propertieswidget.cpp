void PropertiesWidget::loadTorrentInfos(BitTorrent::TorrentHandle *const torrent)
{
    clear();
    m_torrent = torrent;
    downloaded_pieces->setTorrent(m_torrent);
    pieces_availability->setTorrent(m_torrent);
    if (!m_torrent) return;

    // Save path
    updateSavePath(m_torrent);
    // Hash
    hash_lbl->setText(m_torrent->hash());
    PropListModel->model()->clear();
    if (m_torrent->hasMetadata()) {
        // Creation date
        lbl_creationDate->setText(m_torrent->creationDate().toString(Qt::DefaultLocaleShortDate));

        label_total_size_val->setText(Utils::Misc::friendlyUnit(m_torrent->totalSize()));

        // Comment
        comment_text->setText(Utils::Misc::parseHtmlLinks(m_torrent->comment()));

        // URL seeds
        loadUrlSeeds();

        label_created_by_val->setText(m_torrent->creator());

        // List files in torrent
        PropListModel->model()->setupModelData(m_torrent->info());
        filesList->setExpanded(PropListModel->index(0, 0), true);

        // Load file priorities
        PropListModel->model()->updateFilesPriorities(m_torrent->filePriorities());
    }
    // Load dynamic data
    loadDynamicData();
}
