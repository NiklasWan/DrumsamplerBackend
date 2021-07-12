def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.split('.')[-1].lower() in allowed_extensions
