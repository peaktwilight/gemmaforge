  DeletionConfirmationDlg(QWidget *parent, const int &size, const QString &name, bool defaultDeleteFiles): QDialog(parent) {
    setupUi(this);
    if (size == 1)
      label->setText(tr("Are you sure you want to delete '%1' from the transfer list?", "Are you sure you want to delete 'ubuntu-linux-iso' from the transfer list?").arg(name));
    else
      label->setText(tr("Are you sure you want to delete these %1 torrents from the transfer list?", "Are you sure you want to delete these 5 torrents from the transfer list?").arg(QString::number(size)));
    // Icons
    lbl_warn->setPixmap(GuiIconProvider::instance()->getIcon("dialog-warning").pixmap(lbl_warn->height()));
    lbl_warn->setFixedWidth(lbl_warn->height());
    rememberBtn->setIcon(GuiIconProvider::instance()->getIcon("object-locked"));

    move(Utils::Misc::screenCenter(this));
    checkPermDelete->setChecked(defaultDeleteFiles || Preferences::instance()->deleteTorrentFilesAsDefault());
    connect(checkPermDelete, SIGNAL(clicked()), this, SLOT(updateRememberButtonState()));
    buttonBox->button(QDialogButtonBox::Cancel)->setFocus();
  }
