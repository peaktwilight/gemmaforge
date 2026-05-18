void usb_sg_cancel(struct usb_sg_request *io)
{
	unsigned long flags;
	int i, retval;

	spin_lock_irqsave(&io->lock, flags);
	if (io->status || io->count == 0) {
		spin_unlock_irqrestore(&io->lock, flags);
		return;
	}
	/* shut everything down */
	io->status = -ECONNRESET;
	io->count++;		/* Keep the request alive until we're done */
	spin_unlock_irqrestore(&io->lock, flags);

	for (i = io->entries - 1; i >= 0; --i) {
		usb_block_urb(io->urbs[i]);

		retval = usb_unlink_urb(io->urbs[i]);
		if (retval != -EINPROGRESS
		    && retval != -ENODEV
		    && retval != -EBUSY
		    && retval != -EIDRM)
			dev_warn(&io->dev->dev, "%s, unlink --> %d\n",
				 __func__, retval);
	}

	spin_lock_irqsave(&io->lock, flags);
	io->count--;
	if (!io->count)
		complete(&io->complete);
	spin_unlock_irqrestore(&io->lock, flags);
}
