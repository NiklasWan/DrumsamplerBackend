import os

TAGGING_DIR = '/workspaces/backend/tagging'
RECOMMENDATION_DIR = '/workspaces/backend/recommendation'
UPLOAD_FOLDER = '/workspaces/backend/uploads'
ALLOWED_EXTENSIONS = {'wav'}
DATABASE_FILE = 'sqlite:///drumsamp.db'
SECRET_TOKEN = os.getenv('TOKEN_SECRET', 'default_secret')