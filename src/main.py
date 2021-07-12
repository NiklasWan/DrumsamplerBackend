from drumsamp_models import tagger, recommender, ctagger, utils
import configuration as config
from pathlib import Path
from flask import Flask, json
from flask import request, jsonify, make_response, abort
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
from pathlib import Path
import os
from model.Database import db
from util.file_utils import allowed_file
from model.Models import UserModel, SampleModel, TagModel, SampleLibraryModel
from util.http_utils import get_user_from_header, validate_bearer_header

app = Flask(__name__)

UPLOAD_FOLDER = config.UPLOAD_FOLDER
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_FILE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.before_first_request
def init_db():
    db.create_all()

@app.route('/register', methods=['POST'])
def register_user():
    usermail = request.form['mail']
    password = request.form['password']

    if usermail is None or password is None:
        make_response(jsonify({'message': 'Please give both email and password'}), 400)

    if UserModel.query.filter_by(email=usermail).first() is not None:
        return make_response(jsonify({'message': f'User with E-Mail: {usermail} allready exists'}), 400)

    with app.app_context():
        user = UserModel(email=usermail)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return make_response(jsonify({'token': user.encode_auth_token()}), 200)

@app.route('/login', methods=['POST'])
def login_user():
    usermail = request.form['mail']
    password = request.form['password']

    if usermail is None or password is None:
        make_response(jsonify({'message': 'Please give both email and password'}), 400)
    
    user = UserModel.query.filter_by(email=usermail).first()

    if user is None:
        return make_response(jsonify({'message': 'User not existent'}), 404)
    
    if not user.check_password(password):
        return make_response(jsonify({'message': 'Wrong password'}), 400)
    
    return make_response(jsonify({'token': user.encode_auth_token()}), 200)


@app.route('/get/libraries', methods=['GET'])
def get_libraries():
    user = get_user_from_header(request.headers.get('Authorization'))

    if user is None:
        return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

    json_obj = [ l.library_name for l in user.libraries]
    
    return make_response(jsonify(json_obj), 200)

@app.route('/get/library/<library>', methods=['GET'])
def get_library(library):
    usermail = validate_bearer_header(request.headers.get('Authorization'))

    if usermail is None:
        return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)
    
    with app.app_context():
        user = UserModel.query.filter_by(email=usermail).first()
        id=user.id
        _library = SampleLibraryModel.query.filter_by(user_id=user.id, library_name=library).first()
        lib_id = _library.id

        if _library is None:
            return make_response(jsonify({'message': f'No such library {library}'}), 400)

        keys = [s.name for s in _library.samples]

        result = []

    with app.app_context():

        for name in keys:
            samp = SampleModel.query.filter_by(name=name, library_id=lib_id).first()
            result.append({'name': samp.name, 'isFavorite': samp.is_favorite, 'tags': [t.name for t in samp.tags]})

    return make_response(jsonify({'libName': library, 'samples': result}), 200)


@app.route('/upload/<library>', methods=['POST'])
def upload_file(library):
    usermail = validate_bearer_header(request.headers.get('Authorization'))

    if usermail is None:
        return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

    f = request.files['file']
    
    with app.app_context():
        user = UserModel.query.filter_by(email=usermail).first()
        libraries = [ l.library_name for l in user.libraries ]
        id = user.id

        if len(libraries) == 0 or library not in libraries:
            user.libraries.append(SampleLibraryModel(library_name=library))
            db.session.commit()

    base_path = os.path.join(app.config['UPLOAD_FOLDER'], library + '_' + str(id))

    if(not os.path.exists(base_path)):
        os.makedirs(base_path)

    if f and allowed_file(f.filename.split('/')[-1], ALLOWED_EXTENSIONS):
        filename = secure_filename(f.filename.split('/')[-1])

        with app.app_context():
            lib = SampleLibraryModel.query.filter_by(library_name=library, user_id=id).first()  
            lib.samples.append(SampleModel(name=filename.split('.')[0], is_favorite=False))
            db.session.commit()
    
        f.save(os.path.join(base_path, filename))
        return make_response(jsonify({'message': 'Successfully created file'}), 200)
    
    return make_response(jsonify({'message': 'Error in creating file'}), 400)

@app.route('/analyze/<library>', methods=['GET'])
def analyze_files(library):
    usermail = validate_bearer_header(request.headers.get('Authorization'))

    if usermail is None:
        return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

    with app.app_context():
        user = UserModel.query.filter_by(email=usermail).first()
        id = user.id
        _library = SampleLibraryModel.query.filter_by(user_id=user.id, library_name=library).first()

        if _library is None:
            return make_response(jsonify({'message': f'No such library {library}'}), 400)
        
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], library + '_' + str(id))
    classification_path = os.path.join(base_path, 'classification')
    recommendation_path = os.path.join(base_path, 'recommendation')

    if not os.path.exists(classification_path):
        os.makedirs(classification_path)
        
    if not os.path.exists(recommendation_path):
        os.makedirs(recommendation_path)

    files = []
    files.extend(Path(base_path).glob('**/*.wav'))

    files = [str(f) for f in files]

    utils.save_classification_batches_to_disk(files, classification_path)
    utils.save_recommendation_batches_to_disk(files, recommendation_path)

    return make_response(jsonify({'message': 'Analysis completed'}), 200)

@app.route('/tags/<library>', methods=['GET'])
def get_all_tags(library):
    usermail = validate_bearer_header(request.headers.get('Authorization'))

    if usermail is None:
        return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)
    
    with app.app_context():
        user = UserModel.query.filter_by(email=usermail).first()
        id = user.id
        _library = SampleLibraryModel.query.filter_by(user_id=user.id, library_name=library).first()

        if _library is None:
            return make_response(jsonify({'message': f'No such library {library}'}), 400)
    
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], library + '_' + str(id))
    files = []
    classification_path = os.path.join(base_path, 'classification')
    files.extend(Path(classification_path).glob('**/*.npy'))

    files = [str(f) for f in files]

    result = tagger.predict_tags_on_computed_mels(files)

    dictkeys = list(map(lambda x: x.split('/')[-1].split('.')[0] , result.keys()))
    dictvalues = list(result.values())
    tags = list(set(dictvalues))

    # add new tags to db
    for tag in tags:
        with app.app_context():
            _tag = TagModel.query.filter_by(name=tag).first()
            if _tag is None:
                db.session.add(TagModel(name=tag))
                db.session.commit()

    result = dict(zip(dictkeys, dictvalues))

    for name, tag in result.items():
        with app.app_context():
            _library = SampleLibraryModel.query.filter_by(library_name=library, user_id=id).first()
            sample = SampleModel.query.filter_by(name=name, library_id=_library.id).first()
            tags = TagModel.query.all()
            sample_tags = [t.name for t in sample.tags]
            
            if tag not in sample_tags:
                tag_to_insert = TagModel.query.filter_by(name=tag).first()
                sample.tags.append(tag_to_insert)
                db.session.commit()

    with app.app_context():
        _lib = SampleLibraryModel.query.filter_by(user_id=id, library_name=library).first()
        result = [{'name': s.name, 'isFavorite': s.is_favorite, 'tags': [result[s.name]]} for s in _lib.samples]

    return make_response(jsonify({'libName': library, 'samples': result}), 200)

@app.route('/recommendations/<library>', methods=['POST'])
def get_recommendations(library):
    if request.is_json:
        usermail = validate_bearer_header(request.headers.get('Authorization'))

        if usermail is None:
            return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

        with app.app_context():
            user = UserModel.query.filter_by(email=usermail).first()
            id = user.id
            _library = SampleLibraryModel.query.filter_by(user_id=user.id, library_name=library).first()

            if _library is None:
                return make_response(jsonify({'message': f'No such library {library}'}), 400)

        base_path = os.path.join(app.config['UPLOAD_FOLDER'], library + '_' + str(id))
        files = []
        recommendation_path = os.path.join(base_path, 'recommendation')
        files.extend(Path(recommendation_path).glob('**/*.npy'))

        json_array = request.get_json()
        fileNames = [f['name'].split('.')[0] for f in json_array]

        files = [ os.path.join(recommendation_path, f + '.npy') for f in fileNames]

        recommendations = recommender.get_n_most_similar_sounds_mult(15, files, recommendation_path, True)

        recommendations = [ {'name': r[0].split('.')[0]} for r in recommendations ]

        return make_response(jsonify(recommendations), 200)

    return make_response(jsonify({'message': 'Bad Request'}), 400)

@app.route('/usertags/<library>', methods=['POST'])
def get_usertags(library):
    if request.is_json:
        usermail = validate_bearer_header(request.headers.get('Authorization'))

        if usermail is None:
            return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

        with app.app_context():
            user = UserModel.query.filter_by(email=usermail).first()
            id = user.id
            _library = SampleLibraryModel.query.filter_by(user_id=user.id, library_name=library).first()

            if _library is None:
                return make_response(jsonify({'message': f'No such library {library}'}), 400)

        base_path = os.path.join(app.config['UPLOAD_FOLDER'], library + '_' + str(id))
        files = []
        recommendation_path = os.path.join(base_path, 'recommendation')
        files.extend(Path(recommendation_path).glob('**/*.npy'))

        files_to_tag = [str(f) for f in files]

        json_array = request.get_json()

        fileNames = [f['name'].split('.')[0] for f in json_array]

        keys = [ os.path.join(recommendation_path, f + '.npy') for f in fileNames]
        values = [ t['customTags'][0] for t in json_array]
        tag_dict = dict(zip(keys, values))

        result_dict = {}

        for file_to_tag in files_to_tag:
            result_tags = ctagger.get_custom_tag_nearest(file_to_tag, tag_dict, 0.002)

            if len(result_tags) > 0 and file_to_tag not in set(keys):
                filename = file_to_tag.split('/')[-1].split('.')[0]

                with app.app_context():
                    _library = SampleLibraryModel.query.filter_by(library_name=library).first()
                    _sample = SampleModel.query.filter_by(library_id=_library.id, name=filename).first()

                    for t in list(result_tags.keys()):
                        _sample.tags.append(TagModel.query.filter_by(name=t).first())
                    
                    db.session.commit()
                    
                result_dict[filename] = list(result_tags.keys())
            

        return make_response(jsonify(result_dict), 200)
    
    return make_response(jsonify({'message': 'Bad Request'}), 400)

@app.route('/sampletag/update/<library_name>/<sample_name>', methods=['PUT'])
def update_sample_tag(library_name, sample_name):
    if request.is_json:
        usermail = validate_bearer_header(request.headers.get('Authorization'))
        sample_name = sample_name.split('.')[0]

        if usermail is None:
            return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

        with app.app_context():
            library = SampleLibraryModel.query.filter_by(library_name=library_name).first()
            _sample = SampleModel.query.filter_by(library_id=library.id, name=sample_name).first()

            if _sample is None:
                return make_response(jsonify({'message': f'No such sample {sample_name}'}), 400)

        json_data = request.get_json()

        tag_names = json_data['tags']
        
        # add new tags to db
        for tag in tag_names:
            with app.app_context():
                _tag = TagModel.query.filter_by(name=tag).first()
                if _tag is None:
                    db.session.add(TagModel(name=tag))
                    db.session.commit()
        
        with app.app_context():
            sample = SampleModel.query.filter_by(name=sample_name).first()
            tags = TagModel.query.all()
            sample_tags = [t for t in tags if t.name in tag_names]
            
            sample.tags = sample_tags
            db.session.commit()
        
        return make_response(jsonify({'message': 'success'}), 200)

@app.route('/samplefavorite/update/<library_name>/<sample_name>', methods=['PUT'])
def update_sample_favorite(library_name, sample_name):
    if request.is_json:
        usermail = validate_bearer_header(request.headers.get('Authorization'))
        sample_name = sample_name.split('.')[0]

        if usermail is None:
            return make_response(jsonify({'message': 'Token expired. Please login again.'}), 401)

        with app.app_context():
            library = SampleLibraryModel.query.filter_by(library_name=library_name).first()
            _sample = SampleModel.query.filter_by(library_id=library.id, name=sample_name).first()

            if _sample is None:
                return make_response(jsonify({'message': f'No such sample {sample_name}'}), 400)

            json_data = request.get_json()
            _sample.is_favorite = json_data['isFavorite']
            db.session.commit()

        return make_response(jsonify({'message': 'success'}), 200)