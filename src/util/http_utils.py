from model.Models import UserModel

def validate_bearer_header(header):
    if header is None:
        return False
    
    token = header.split(' ')[-1]

    return UserModel.decode_auth_token(token)

def get_user_from_header(header):
    usermail = validate_bearer_header(header)

    if usermail is None:
        return None
    
    return UserModel.query.filter_by(email=usermail).first()