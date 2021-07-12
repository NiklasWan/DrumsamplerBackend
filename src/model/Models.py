from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from model.Database import db
import jwt
import configuration as config
import datetime

sample_tags = db.Table('sample_tags',
    db.Column('sample_id', db.Integer, db.ForeignKey('sample.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class UserModel(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, unique=True)
    password_hash = db.Column(db.Text)
    libraries = db.relationship('SampleLibraryModel', backref='user', lazy="dynamic")

    def set_password(self, password):
	    self.password_hash = generate_password_hash(password)
	
    def check_password(self, password):
	    return check_password_hash(self.password_hash, password)
    
    def encode_auth_token(self):
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30),
                'iat': datetime.datetime.utcnow(),
                'sub': self.email
            }

            return jwt.encode(
                payload,
                config.SECRET_TOKEN,
                algorithm='HS256'
            )
        except Exception as e:
            return e

    # Taken from https://realpython.com/token-based-authentication-with-flask/
    @staticmethod
    def decode_auth_token(auth_token):
        try:
            payload = jwt.decode(auth_token, config.SECRET_TOKEN, algorithms='HS256')
            return payload['sub']
        except:
            return None

class SampleLibraryModel(db.Model):
    __tablename__ = 'samplelibrary'
    
    id = db.Column(db.Integer, primary_key=True)
    library_name = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    samples = db.relationship('SampleModel', backref='samplelibrary', lazy="dynamic")

class SampleModel(db.Model):
    __tablename__ = 'sample'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    is_favorite = db.Column(db.Boolean, nullable=False)
    library_id = db.Column(db.Integer, db.ForeignKey('samplelibrary.id'),
        nullable=False)
    tags = db.relationship('TagModel', secondary=sample_tags, lazy='subquery',
        	backref=db.backref('sample', lazy="dynamic"))

class TagModel(db.Model):
	__tablename__ = 'tag'

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Text, nullable=False, unique=True)