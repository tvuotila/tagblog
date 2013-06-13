import math
import os
from flask import (Flask, render_template, Markup, 
                    abort, redirect, url_for, request, flash)
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser)
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.wtf import Form
from sqlalchemy.exc import IntegrityError
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms.validators import DataRequired, Length
from wtforms import (TextField, PasswordField, TextAreaField, 
                    SelectMultipleField, HiddenField, FieldList, FormField)

app = Flask(__name__)
# Get setting from file specified in enviroment variables or default file.
# This way we can change settings while testing.
app.config.from_pyfile(os.environ.get('TAGBLOG_SETTINGS_FILE', 'settings.py'))
app.secret_key = os.environ['SECRET_KEY']
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

class User(db.Model):
    """Model for user of tagblog website."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    _pw_hash = db.Column(db.String(170))
    
    def __init__(self, username, password):
        """Create new user.

        Keyword arguments:
        username -- max 80 length string
        password -- password for the user

        """
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        """Save password hash."""
        self._pw_hash = generate_password_hash(password)

    def check_password(self, password):
        """Validate password against password hash."""
        return check_password_hash(self._pw_hash, password)

    def is_authenticated(self):
        """Check if user has authenticated. 

        Non-anonymous user is always authenticated.

        """
        return True

    def is_active(self):
        """Check if user is active. 

        Non-anonymous user is always active.

        """
        return True

    def is_anonymous(self):
        """Check if user is anonymous."""
        return False

    def get_id(self):
        """Returns unique unicode id for the user."""
        return unicode(self.id)

    def is_admin(self):
        """Check if user is admin. 

        Currently we only have admin users.
        Non-anonymous user is admin.

        """
        return True

# Helper table for tag-blogpost relationship
tagsTable = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('blogpost_id', db.Integer, db.ForeignKey('blogpost.id'))
    )

class Tag(db.Model):
    """Model for tags"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '<Tag: ' + str(self.name) + '>'

class Blogpost(db.Model):
    """Model for blogpost.

    Blogpost consisting of title, body and tags.

    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    tags = db.relationship('Tag', secondary=tagsTable, 
        backref=db.backref('blogposts', lazy='dynamic'))

    def __init__(self, title, body, tags=None):
        """
        Create a new blogpost.

        Keyword arguments:
        title -- title for the post. max 80 length string
        body -- text of the post. multiline string
        tags -- list of tags of the post as Tag objects

        """
        self.title = title
        self.body = body
        self.tags = tags

    def add_tag(self, tag):
        """Add new tag to post."""
        self.tags.append(tag)

# Create database
db.create_all()

@login_manager.user_loader
def load_user(userid):
    """Return user or None if user not found.

    Keyword arguments:
    userid --- unicode identifier of the user

    """
    try:
        return User.query.filter_by(id=int(userid)).first()
    except Exception, e:
        return None

class LoginForm(Form):
    """Form for logging in a user."""
    username = TextField(label=u'username', description=u'username', 
                        validators=[DataRequired(), Length(max=80)])
    password = PasswordField(label=u'password', description=u'password', 
                        validators=[DataRequired()])

class BlogpostForm(Form):
    """Form for inputing blog post info."""
    id = HiddenField()
    title = TextField(label=u'Title', description=u'title of the post', 
                        validators=[Length(max=80)])
    body = TextAreaField(label=u'Body', description=u'body of the post')
    tags = SelectMultipleField(label=u'Tags', description=u'tags of the post',
                        coerce=int)

    def __init__(self, formdata=None, obj=None, 
                prefix='', post=None, **kwargs):
        """Create a new form.

        Keyword arguments:
        formdata --- array to fill the form with. \
        Defaults to request.form. Pass None to prevent it.
        obj --- deprecated, use post keyword instead. \
        left here for backward compatibility. object to fill the form with. 
        prefix --- string to prefix form field names with.
        post --- post object to fill form fields with.
        Other arguments are passed to parent class's constructor.

        """
        super(BlogpostForm, self)
            .__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)
        self.post_init()
        if post:
            self.id.data = post.id
            self.title.data = post.title
            self.body.data = post.body
            self.tags.data = [t.id for t in post.tags]

    def post_init(self):
        """Update possible tags."""
        self.tags.choices = [(t.id, t.name) 
                            for t in Tag.query.order_by('name').all()]

class SingleTagForm(Form):
    """Form for inputting tag info for a tag."""
    id = HiddenField()
    name = TextField('Tag', validators=[DataRequired()])

class TagForm(Form):
    """Form for inputting tag info for multiple tags."""
    tags = FieldList(FormField(SingleTagForm))

def redirect_next_or_index():
    """
    Return page to redirect to.

    Helper method for redirecting:
    Tries to find 'next' info and redirect there.
    If next info not found, will redirect to index page. 

    """
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

@app.route('/<page>')
@app.route('/')
def index(page=1):
    """Index page listing all blogposts."""
    page = max(int(page), 1)
    posts = Blogpost.query.limit(10).offset((page-1)*10).all()
    # How many pages of posts we have
    pages = int(math.ceil(float(Blogpost.query.count())/10))
    return render_template('index.html', 
                            posts=posts, 
                            pages=pages, 
                            page=page, 
                            loginform=LoginForm(), 
                            addpostform=BlogpostForm())

@app.route('/search')
def search():
    """Page for searching posts"""
    try:
        queryString = request.values['query']
        .replace('/','//').replace('%','/%')
        .replace('_','/_')
    except KeyError:
        flash('Search query not present')
        return redirect_next_or_index()
    # Try to get page from GET or POST data.
    # Fall back to 1 if fails or <1.
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
        return render_template('search.html', 
                                posts=[], 
                                pages=0, 
                                page=page, 
                                loginform=LoginForm(), 
                                addpostform=BlogpostForm()) 
    # I will leave database optimization to database engine.
    query = Blogpost.query
    for term in terms:
        query1 = Blogpost.query.filter(Blogpost.title.like('%'+term+'%'))
        query2 = Blogpost.query.filter(Blogpost.body.like('%'+term+'%'))
        query = query.intersect(query1.union(query2))
    posts = query.limit(10).offset((page-1)*10).all()
    pages = int(math.ceil(float(query.count())/10))
    return render_template('search.html', 
                            posts=posts, 
                            pages=pages, 
                            page=page, 
                            loginform=LoginForm(), 
                            addpostform=BlogpostForm())

@app.route('/edittags', methods=('GET', 'POST'))
@login_required
def edittags():
    """Page for editing tags.

    If request is get, show page to edit tags.
    If request is post, edit tags and redirect to get.

    """
    if request.method == 'GET':
        tagForm = TagForm()
        tags = Tag.query.all()
        for tag in tags:
            tagForm.tags.append_entry(data={'id':tag.id, 'name':tag.name})
        # We need at leat one entry
        if len(tags) < 1:
            tagForm.tags.append_entry()
        return render_template('edittags.html', \
                                tagform=tagForm, \
                                loginform=LoginForm(), \
                                addpostform=BlogpostForm())
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
            app.logger.debug('Removing '+
                str(
                    Tag.query.filter(
                        Tag.id.notin_(ids)).delete(synchronize_session=False))
                +' tags')
        # db.session.commit() # When sure, we delete
        # We need to still update old tags.
        # Lets first load all tags to memory so that
        # no extra sql queries are needed.
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
            flash('Got integrity error. \
                Sure you didn\'t give same name to two or more tags?')
            # Should do this automatically. Can't be too sure.
            # Let's rollback changes
            db.session.rollback()
        return redirect(url_for('edittags'))
    # Fall-back
    flash('Internal error')
    return redirect_next_or_index()

@app.route('/addpost', methods=('GET', 'POST'))
@login_required
def addpost():
    """Page for adding new post. Post info must be as form data."""
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
    """Page for editing a post. Post info must be as form data."""
    try:
        editpostform = BlogpostForm(request.form)
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

@app.route('/deletepost', methods=('GET', 'POST'))
@login_required
def deletepost():
    """Page for deleting a post. 

    Id of the post to delete must be in postid value.

    """
    id = request.values['postid']
    Blogpost.query.filter_by(id=id).delete()
    db.session.commit()
    flash('Deleted the post')
    return redirect_next_or_index()

@app.route('/post/<id>')
def post(id):
    """Page for viewing the post.

    Keyword arguments:
    id --- id of the post to show

    """
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
    """Page that logs in the user. Login data must be as form data"""
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
    """Logout current user."""
    logout_user()
    return redirect_next_or_index()

if __name__ == '__main__':
    app.run(debug=True)