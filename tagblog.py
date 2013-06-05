import math
from flask import Flask, render_template, Markup, abort, redirect, url_for, request, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser)
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.wtf import Form
from sqlalchemy.exc import IntegrityError
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms.validators import DataRequired, Length
from wtforms import TextField, PasswordField, TextAreaField, SelectMultipleField, HiddenField, FieldList, FormField

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
tagsTable = db.Table('tags',
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

    def __str__(self):
        return '<Tag: ' + str(self.name) + '>'


# Blog post consisting of title, body and tags.
class Blogpost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    tags = db.relationship('Tag', secondary=tagsTable, 
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

class BlogpostForm(Form):
    id = HiddenField()
    title = TextField(label=u'Title', description=u'title of the post', validators=[Length(max=80)])
    body = TextAreaField(label=u'Body', description=u'body of the post')
    tags = SelectMultipleField(label=u'Tags', description=u'tags of the post', coerce=int)

    def __init__(self, formdata=None, obj=None, prefix='', post=None, **kwargs):
        super(BlogpostForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)
        self.post_init()
        if post:
            self.id.data = post.id
            self.title.data = post.title
            self.body.data = post.body
            self.tags.data = [t.id for t in post.tags]

    # used to init tags with correct values
    def post_init(self):
        self.tags.choices = [(t.id, t.name) for t in Tag.query.order_by('name').all()]

class SingleTagForm(Form):
    id = HiddenField()
    name = TextField('Tag', validators=[DataRequired()])

class TagForm(Form):
    tags = FieldList(FormField(SingleTagForm))

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
def index(page=1):
    page = max(int(page), 1)
    posts = Blogpost.query.limit(10).offset((page-1)*10).all()
    # How many pages of posts we have
    pages = int(math.ceil(float(Blogpost.query.count())/10))
    return render_template('index.html', posts=posts, pages=pages, page=page, loginform=LoginForm(), addpostform=BlogpostForm())

# Page for searching posts
@app.route('/search')
def search():
    try:
        queryString = request.values['query'].replace('/','//').replace('%','/%').replace('_','/_')
    except KeyError:
        flash('Search query not present')
        return redirect_next_or_index()
    # Try to get page from GET or POST data.
    # Fall back to 1 if fails or <1
    page = 1
    try:
        page = int(request.values['page'])
    except:
        pass
    page = max(page, 1)
    terms = queryString.split()
    # Maximum amount of terms is 11 or things will crash.
    if len(terms) > 11:
        flash('Too many search terms. 11 is maximum.')
        return render_template('search.html', posts=[], pages=0, page=page, loginform=LoginForm(), addpostform=BlogpostForm()) 
    # I will leave database optimization to database engine.
    query = Blogpost.query
    for term in terms:
        query1 = Blogpost.query.filter(Blogpost.title.like('%'+term+'%'))
        query2 = Blogpost.query.filter(Blogpost.body.like('%'+term+'%'))
        query = query.intersect(query1.union(query2))
    posts = query.limit(10).offset((page-1)*10).all()
    pages = int(math.ceil(float(query.count())/10))
    return render_template('search.html', posts=posts, pages=pages, page=page, loginform=LoginForm(), addpostform=BlogpostForm())

# Page for editing tags
@app.route('/edittags', methods=('GET', 'POST'))
@login_required
def edittags():
    if request.method == 'GET':
        tagForm = TagForm()
        tags = Tag.query.all()
        for tag in tags:
            tagForm.tags.append_entry(data={'id':tag.id, 'name':tag.name})
        # We need at leat one entry
        if len(tags) < 1:
            tagForm.tags.append_entry()
        return render_template('edittags.html', tagform=tagForm, loginform=LoginForm(), addpostform=BlogpostForm())
    else:
        tagForm = TagForm(request.form)
        tags = []
        for entry in tagForm.tags.entries:
            tags.append((entry.data['id'], entry.data['name']))
        # First lets remove all empty lines.
        tags[:] = [tag for tag in tags if not (tag[1] == u'')]
        # New entries have no id
        newEntries = [tag for tag in tags if (tag[0] == u'')]
        # We have them in separate list so lets remove them from first
        tags[:] = [tag for tag in tags if not tag in newEntries]
        # Lets remove tags that were not returned
        ids = [int(tag[0]) for tag in tags]
        if ids:
            #  Delete dosen't work right without this
            db.session.commit()
            app.logger.debug('Removing '+str(Tag.query.filter(Tag.id.notin_(ids)).delete(synchronize_session=False))+' tags')
        # db.session.commit() # When sure, we delete
        # We need to still update old tags.
        # Lets first load all tags to memory so that no extra sql queries are needed.
        # After all we edit every tag.
        tmpTags = Tag.query.all()
        for tag in tags:
            try:
                updatedTag = Tag.query.get(int(tag[0]))
                updatedTag.name = tag[1]
                db.session.add(updatedTag)
            except:
                app.logger.warning('Error retrieving tag: '+tag[0])
        # Add new entries
        for entry in newEntries:
            tag = Tag(entry[1])
            db.session.add(tag)
        # Commit changes
        try:
            db.session.commit()
            flash('Tags saved')
        except IntegrityError, e:
            flash('Got integrity error. Sure you didn\'t give same name to two or more tags?')
            # Should do this automatically. Can't be too sure.
            # Let's rollback changes
            db.session.rollback()
        return redirect(url_for('edittags'))


# Page for adding new post
@app.route('/addpost', methods=('GET', 'POST'))
@login_required
def addpost():
    try:
        addpostform = BlogpostForm(request.form)
        if addpostform.validate_on_submit():
            title = addpostform.title.data
            body = addpostform.body.data
            tags = [int(tag) for tag in addpostform.tags.data]
            if tags: 
                tags = Tag.query.filter(Tag.id.in_(tags)).all()
            post = Blogpost(title, body, tags)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('post', id=post.id))
    except Exception, e:
        app.logger.warning(str(e))
    flash('Internal error')
    return redirect_next_or_index()

@app.route('/editpost', methods=('GET', 'POST'))
@login_required
def editpost():
    try:
        editpostform = BlogpostForm(request.form)
        editpostform.post_init()
        if editpostform.validate_on_submit():
            post = Blogpost.query.get(editpostform.id.data)
            if not post:
                flash('Blogpost not found')
                redirect_next_or_index()
            post.title = editpostform.title.data
            post.body = editpostform.body.data
            tags = editpostform.tags.data
            if tags: 
                tags = Tag.query.filter(Tag.id.in_(tags)).all()
            post.tags = tags
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('post', id=post.id))
        else:
            app.logger.warning(str(editpostform.errors))
    except Exception, e:
        raise
    flash('Internal error')
    return redirect_next_or_index()

# Page for viewing the post
@app.route('/post/<id>')
def post(id):
    try:
        post = Blogpost.query.filter_by(id=id).first()
        if post:
            editpostform = BlogpostForm(post=post)
            return render_template('post.html', post=post, id=id, editpostform=editpostform, loginform=LoginForm(), addpostform=BlogpostForm())
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
    return redirect_next_or_index()

if __name__ == '__main__':
    app.run(debug=True)