def handle_file(u: Profile, headline: str, category: str, text: str, file):
    m: Media = Media()
    upload_base_path: str = 'uploads/' + str(date.today().year)
    high_res_file_name = upload_base_path + '/HIGHRES_' + ntpath.basename(file.name.replace(" ", "_"))
    low_res_file_name = upload_base_path + '/LOWRES_' + ntpath.basename(file.name.replace(" ", "_"))
    if not os.path.exists(PATH_TO_UPLOAD_FOLDER_ON_DISK + upload_base_path):
        os.makedirs(PATH_TO_UPLOAD_FOLDER_ON_DISK + upload_base_path)
    with open(high_res_file_name, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    # TODO crop image
    original = Image.open(high_res_file_name)
    width, height = original.size
    diameter = math.sqrt(math.pow(width, 2) + math.pow(height, 2))
    width /= diameter
    height /= diameter
    width *= IMAGE_SCALE
    height *= IMAGE_SCALE
    cropped = original.resize((int(width), int(height)), PIL.Image.LANCZOS)
    cropped.save(low_res_file_name)
    m.text = escape(text)
    m.cachedText = compile_markdown(escape(text))
    m.category = escape(category)
    m.highResFile = "/" + high_res_file_name
    m.lowResFile = "/" + low_res_file_name
    m.headline = escape(headline)
    m.save()
    mu: MediaUpload = MediaUpload()
    mu.UID = u
    mu.MID = m
    mu.save()
    logging.info("Uploaded file '" + str(file.name) + "' and cropped it. The resulting PK is " + str(m.pk))
