import os

TAGGING_DIR = '/workspaces/DrumsamplerBackend/tagging'
RECOMMENDATION_DIR = '/workspaces/DrumsamplerBackend/recommendation'
UPLOAD_FOLDER = '/workspaces/DrumsamplerBackend/uploads'
ALLOWED_EXTENSIONS = {'wav'}
DATABASE_FILE = 'sqlite:///drumsamp.db'
SECRET_TOKEN = os.getenv('TOKEN_SECRET', 'default_secret')