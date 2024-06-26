from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required
from werkzeug.utils import secure_filename #REMOVE
import os
from functions import validate_file
from flask import current_app as app

from auth import auth_bp
from models import db, User, UserInfo

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='') # Creates Flask Instance. Arguments is where static compiled frontend files are.
app.config['SECRET_KEY'] = 'someSecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../frontend/src/store/uploads') # For flask image upload

CORS(app, supports_credentials=True)
db.init_app(app)

# flask login setup
lim = LoginManager()
lim.login_view = 'auth.login'
lim.init_app(app)

@lim.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# flask login setup

app.register_blueprint(auth_bp)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Uploading profile picture
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'photo' not in request.files:
        app.logger("no file part")
        return jsonify({'message': 'No file part'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    error = validate_file(file)
    if error:
        app.logger.error(f"File validation error: {error}")
        return jsonify({"message": error}), 400

    if file:
        #Forcing name
        unique_filename = f"user_{current_user.id}_profile.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        #Overwriting previous, to avoid many uploads
        file.save(filepath)
        
        # Update profile pic in db
        user = User.query.get(current_user.id)
        user.profileImg = unique_filename
        db.session.commit()

        app.logger.info(f"File uploaded successfully: {unique_filename}")
        return jsonify({'filename': unique_filename}), 200
    
    return jsonify({'message': 'File upload failed'}), 500

@app.route('/store/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
@app.route('/api/allusers', methods=['GET'])
@login_required
def get_all_users():
    users = User.query.all()
    user_list = [{'username': user.username, 'profileImg': user.profileImg} for user in users]
    return jsonify(user_list), 200


# @app.route('/api/user_info/<username>', methods=['GET'])
# @login_required
# def get_user_info(username):
#     if not username:
#         app.logger.info("Username not received on backend")
#         return jsonify({'message': 'No username provided'}), 400
    
#     user = User.query.filter_by(username=username).first()
#     if not user:
#         app.logger.info("No user found Oo")
#         return jsonify({'message': 'No user found Oo'}), 404

#     user_info = UserInfo.query.filter_by(user_id=user.id).first()
#     if not user_info:
#         app.logger.info("No user INFO found !")
#         return jsonify({
#         'username': user.username,
#         'work': 'None',
#         'education': 'None',
#         'hobbies': 'None',
#         'age': 1,
#         'location': 'None',
#         'bio': 'None'
#         }), 200

#     return jsonify({
#         'username': user.username,
#         'work': user_info.work,
#         'education': user_info.education,
#         'hobbies': user_info.hobbies,
#         'age': user_info.age,
#         'location': user_info.location,
#         'bio': user_info.bio
#     }), 200

@app.route('/api/user_info/<username>', methods=['GET'])
@login_required
def get_user_info(username):
    if not username:
        app.logger.info("Username not received on backend")
        return jsonify({'message': 'No username provided'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        app.logger.info("No user found Oo")
        return jsonify({'message': 'No user found Oo'}), 404

    user_info = UserInfo.query.filter_by(user_id=user.id).first()

    return jsonify({
        'username': user.username,
        'work': user_info.work if user_info else "",
        'education': user_info.education if user_info else "",
        'hobbies': user_info.hobbies if user_info else "",
        'age': user_info.age if user_info else "",
        'location': user_info.location if user_info else "",
        'bio': user_info.bio if user_info else "",
        'profileImg': user.profileImg if user_info else None
    }), 200


@app.route('/api/user_info', methods=['POST'])
@login_required
def update_user_info():
    data = request.get_json()
    username = data.get('username')
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    user_info = UserInfo.query.filter_by(user_id=user.id).first()
    if not user_info:
        user_info = UserInfo(user_id=user.id)
        db.session.add(user_info)

    work = data.get('work', user_info.work)
    if not isinstance(work, str) or len(work) > 15:
        return jsonify({'message': 'Work must be a string and less than 15 characters'}), 400

    education = data.get('education', user_info.education)
    if not isinstance(education, str) or len(education) > 15:
        return jsonify({'message': 'Education must be a string and less than 15 characters'}), 400

    hobbies = data.get('hobbies', user_info.hobbies)
    if not isinstance(hobbies, str) or len(hobbies) > 15:
        return jsonify({'message': 'Hobbies must be a string and less than 15 characters'}), 400

    age = data.get('age', user_info.age)
    if not isinstance(age, int) or age < 0 or age > 300:
        return jsonify({'message': 'Age must be a number between 0 and 300'}), 400

    location = data.get('location', user_info.location)
    if not isinstance(location, str) or len(location) > 15:
        return jsonify({'message': 'Location must be a string and less than 15 characters'}), 400

    bio = data.get('bio', user_info.bio)
    if not isinstance(bio, str) or len(bio) > 100:
        return jsonify({'message': 'Bio must be a string and less than 100 characters'}), 400

    user_info.work = data.get('work', user_info.work)
    user_info.education = data.get('education', user_info.education)
    user_info.hobbies = data.get('hobbies', user_info.hobbies)
    user_info.age = data.get('age', user_info.age)
    user_info.location = data.get('location', user_info.location)
    user_info.bio = data.get('bio', user_info.bio)

    db.session.commit()

    return jsonify({'message': 'User info updated successfully'}), 200

@app.route('/api/users_by_education', methods=['POST'])
@login_required
def get_users_by_education():
    data = request.get_json()
    education = data.get('education')

    if not education:
        return jsonify({'message': 'No education provided'}), 400

    users = User.query.join(UserInfo).filter(UserInfo.education.ilike(f"%{education}%")).all()
    if not users:
        return jsonify([]), 200

    return jsonify([{'username': user.username, 'profileImg': user.profileImg} for user in users]), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database and tables
    app.run(debug=True)


