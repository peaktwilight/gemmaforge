rdpBitmapCache* bitmap_cache_new(rdpSettings* settings)
{
	int i;
	rdpBitmapCache* bitmapCache;
	bitmapCache = (rdpBitmapCache*)calloc(1, sizeof(rdpBitmapCache));

	if (!bitmapCache)
		return NULL;

	bitmapCache->settings = settings;
	bitmapCache->update = ((freerdp*)settings->instance)->update;
	bitmapCache->context = bitmapCache->update->context;
	bitmapCache->cells =
	    (BITMAP_V2_CELL*)calloc(settings->BitmapCacheV2NumCells, sizeof(BITMAP_V2_CELL));

	if (!bitmapCache->cells)
		goto fail;
	bitmapCache->maxCells = settings->BitmapCacheV2NumCells;

	for (i = 0; i < (int)bitmapCache->maxCells; i++)
	{
		bitmapCache->cells[i].number = settings->BitmapCacheV2CellInfo[i].numEntries;
		/* allocate an extra entry for BITMAP_CACHE_WAITING_LIST_INDEX */
		bitmapCache->cells[i].entries =
		    (rdpBitmap**)calloc((bitmapCache->cells[i].number + 1), sizeof(rdpBitmap*));

		if (!bitmapCache->cells[i].entries)
			goto fail;
	}

	return bitmapCache;
fail:

	if (bitmapCache->cells)
	{
		for (i = 0; i < (int)bitmapCache->maxCells; i++)
			free(bitmapCache->cells[i].entries);
	}

	free(bitmapCache);
	return NULL;
}
