from flask import Flask, render_template, Markup, abort, redirect, url_for, request, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser)
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.wtf import Form
from wtforms.validators import DataRequired, Length
from wtforms import TextField, PasswordField

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

    # Currently we only have admins.
    def is_admin(self):
        return True

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
        return User.query.filter_by(id=int(userid)).first()
    except Exception, e:
        return None

class LoginForm(Form):
    username = TextField(label=u'username', description=u'username', validators=[DataRequired(), Length(max=80)])
    password = PasswordField(label=u'password', description=u'password', validators=[DataRequired()])

# Helper method for redirecting
# Tries to find 'next' info and redirect there.
# If next info not found, will redirect to index page. 
def redirect_next_or_index():
    try:
        if request.values['next'] == None:
            app.logger.debug('No next field')
            return redirect(url_for('index'))
        else:
            app.logger.debug('next field is '+request.values['next'])
            return redirect(request.values['next'])
    except Exception, e:
        app.logger.warning(str(e))
    # fall-back
    return redirect(url_for('index'))

# Index listing all blogposts
@app.route('/<page>')
@app.route('/')
def index(page=0):
    posts = Blogpost.query.limit(20).offset(page*20).all()
    return render_template('index.html', posts=posts, loginform=LoginForm())

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
    try:
        post = Blogpost.query.filter_by(id=id).first()
        if post:
            return render_template('post.html',post=post, loginform=LoginForm())
    except Exception, e:
        app.logger.warning(str(e))
    return redirect_next_or_index()
    

@app.route('/login', methods=('GET', 'POST'))
def login():
    # fail-fast if not trying to login
    if not request.form:
        return redirect(url_for('index'))
    # get login data and validate it
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user==None or not user.check_password(form.password.data):
            app.logger.debug('user not found or invalid password. User is ' + (user.username if user else '<None>'))
            flash('invalid credentials')
            return redirect(url_for('index'))
        else:
            login_user(user)
            app.logger.debug('logged in user: '+user.username)
    for error in form.errors:
        flash(error)
    return redirect_next_or_index()

    

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)