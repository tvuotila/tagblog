from flask import Flask, render_template, Markup, abort, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_pyfile('settings.py')
app.secret_key = '\xcaI\x9f\r+\xd4\xae4<\x1f\x87!r\xe3\xc9\xf2Jh+\xc2\x95\x17\x9e\x98'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    pw_hash = db.Column(db.String(170))

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

# Helper table for tag-blogpost relationship
tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('blogpost_id', db.Integer, db.ForeignKey('blogpost.id'))
)

# Tag
class Tag(db.Model):
    """A tag"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Tag: ' + self.name + '>'


# Blog post consisting of title, body and tags.
class Blogpost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    tags = db.relationship('Tag', secondary=tags, 
        backref=db.backref('blogposts', lazy='dynamic'))

    def __init__(self, title, body, tags=None):
        self.title = title
        self.body = body
        self.tags = tags

    def add_tag(self, tag):
        self.tags.append(tag)

# Create database
db.create_all()

@login_manager.user_loader
def load_user(userid):
    try:
        return User.query.filter_by(id=int(userid))
    except Exception, e:
        return None
    

# Index listing all blogposts
@app.route('/<page>')
@app.route('/')
def index(page=0):
    posts = Blogpost.query.limit(20).offset(page*20).all()
    return render_template('index.html', posts=posts)

# Page for searching posts
@app.route('/search')
def search():
    pass

# Page for editing tags
@app.route('/edittags')
@login_required
def edittags():
    pass

# Page for viewing the post
@app.route('/post/<id>')
def post(id):
    pass

@app.route('/login')
def login():
    print  request.args.get("next")
    pass

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logget out.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)