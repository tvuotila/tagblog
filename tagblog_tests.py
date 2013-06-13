import os
#Lets use test settings
os.environ['TAGBLOG_SETTINGS_FILE'] = 'test_settings.py'
import tagblog
import unittest
import tempfile
from flask.ext.sqlalchemy import SQLAlchemy

class TagblogTestCase(unittest.TestCase):
    """Test tagblog library/site"""

    def setUp(self):
        self.app = tagblog.app.test_client()
        # Empty table
        tagblog.db.drop_all()
        tagblog.db.create_all()
        # Create test user
        tagblog.db.session.add(tagblog.User('admin', 'default'))
        tagblog.db.session.commit()

    def tearDown(self):
        # Empty session
        tagblog.db.session.rollback()
        # Empty table
        tagblog.db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
                            username=username,
                            password=password
                            ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_empty_db(self):
        # Database empty
        assert tagblog.Blogpost.query.count() == 0
        assert tagblog.Tag.query.count() == 0
        assert tagblog.User.query.count() == 1

        rv = self.app.get('/')
        # In
        assert 'Tagblog' in rv.data
        assert 'Home' in rv.data
        assert 'Sign in' in rv.data
        # Not in
        assert 'Edit tags' not in rv.data
        assert 'Add new post' not in rv.data
        assert 'Hello' not in rv.data
        # A way to check that no posts have been added
        assert 'Tags:' not in rv.data

    def test_login_logout(self):
        # Authorized login
        rv = self.login('admin', 'default')
        # In
        assert 'Hello, admin' in rv.data
        assert 'Logout' in rv.data
        # Not in
        assert 'Sign in' not in rv.data

        # Logging out
        rv = self.logout()
        # In
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

        # Un-authorized login
        # Wrong username
        rv = self.login('adminx', 'default')
        # In
        assert 'invalid credentials' in rv.data
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

        # Un-authorized login
        # Wrong password
        rv = self.login('admin', 'defaultx')
        # In
        assert 'invalid credentials' in rv.data
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

    def test_tags(self):
        # First we have empty tag database.
        assert tagblog.Tag.query.count() == 0
        self.app.post('/edittags', data={
                            'tags-0-id':'', 
                            'tags-0-name':'testingtag1'})
        # Previous should fail.
        assert tagblog.Tag.query.count() == 0
        self.login('admin', 'default')
        self.app.post('/edittags', data={
                            'tags-0-id':'', 
                            'tags-0-name':'testingtag1'})
        assert tagblog.Tag.query.count() == 1
        assert tagblog.Tag.query.first().name == 'testingtag1'
        # Change tag
        tag = tagblog.Tag.query.first()
        self.app.post('/edittags', data={
                            'tags-0-id':tag.id, 
                            'tags-0-name':'testingtag2'})
        assert tagblog.Tag.query.count() == 1
        assert tagblog.Tag.query.first().name == 'testingtag2'
        # Add another tag
        self.app.post('/edittags', data={
                            'tags-0-id':'', 
                            'tags-0-name':'anothertestingtag'})
        assert tagblog.Tag.query.count() == 2
        assert tagblog.Tag.query.filter_by(name='testingtag2').count() == 1
        assert (tagblog.Tag.query.filter_by(name='anothertestingtag').count()   == 1)

    def test_blogpost_add(self):
        # First there is no posts.
        assert tagblog.Blogpost.query.count() == 0
        # Unauthorized add
        self.app.post('/addpost',data={
                            'title':'titletext',
                            'body':'bodytext'})
        assert tagblog.Blogpost.query.count() == 0
        self.login('admin', 'default')
        self.app.post('/addpost',data={
                            'title':'titletext',
                            'body':'bodytext'})
        assert tagblog.Blogpost.query.count() == 1
        assert tagblog.Blogpost.query.first().title == 'titletext'
        assert tagblog.Blogpost.query.first().body == 'bodytext'
        assert not tagblog.Blogpost.query.first().tags
        # Test tagged Blogs
        tag1 = tagblog.Tag('tagOne')
        tag2 = tagblog.Tag('tagTwo')
        tagblog.db.session.add(tag1)
        tagblog.db.session.add(tag2)
        tagblog.db.session.commit()
        # Post with one tag
        self.app.post('/addpost',data={
                            'title':'titletext2',
                            'body':'bodytext2',
                            'tags':[tag1.id]})
        assert tagblog.Blogpost.query.count() == 2
        post = tagblog.Blogpost.query.filter_by(title='titletext2',
                                                body='bodytext2').one()
        assert post
        # Let's add tags to session so that we can use them.
        tagblog.db.session.add(tag1)
        tagblog.db.session.add(tag2)
        assert tag1 in post.tags
        assert not tag2 in post.tags
        # Post with two tags
        self.app.post('/addpost',data={
                            'title':'titletext3',
                            'body':'bodytext3',
                            'tags':[tag1.id, tag2.id]})
        assert tagblog.Blogpost.query.count() == 3
        post = tagblog.Blogpost.query.filter_by(title='titletext3',
                                                body='bodytext3').one()
        assert post
        # Let's add tags to session so that we can use them.
        tagblog.db.session.add(tag1)
        tagblog.db.session.add(tag2)
        assert tag1 in post.tags
        assert tag2 in post.tags

    def test_blogpost_edit(self):
        # Let's add some posts
        first = tagblog.Tag('First')
        second = tagblog.Tag('second')
        third = tagblog.Tag('third')
        not_first = tagblog.Tag('not first')
        last = tagblog.Tag('last')
        post1 = tagblog.Blogpost('title1','body1',[first])
        post2 = tagblog.Blogpost('title2','body2',[second, not_first])
        post3 = tagblog.Blogpost('title3','body3',[third, not_first, last])
        tagblog.db.session.add_all([post1, post2, post3])
        tagblog.db.session.commit()
        # Check if posts show right
        rv = self.app.get('/')
        assert 'title1' in rv.data
        assert 'body1' in rv.data
        assert 'Tags:' in rv.data
        assert 'First' in rv.data
        assert 'title2' in rv.data
        assert 'body2' in rv.data
        assert 'second' in rv.data
        assert 'not first' in rv.data
        assert 'title3' in rv.data
        assert 'body3' in rv.data
        assert 'third' in rv.data
        assert 'last' in rv.data
        # Let's edit the first one
        # unauthorized edit
        tagblog.db.session.add(post1)
        self.app.post('/editpost',data={
                            'id':post1.id,
                            'title':'editedtItle1',
                            'body':'editedbOdy1'})
        # Things should not change
        rv = self.app.get('/')
        assert 'title1' in rv.data
        assert 'body1' in rv.data
        assert 'Tags:' in rv.data
        assert 'First' in rv.data
        assert 'title2' in rv.data
        assert 'body2' in rv.data
        assert 'second' in rv.data
        assert 'not first' in rv.data
        assert 'title3' in rv.data
        assert 'body3' in rv.data
        assert 'third' in rv.data
        assert 'last' in rv.data
        assert 'editedtItle1' not in rv.data
        assert 'editedbOdy1' not in rv.data
        #Authorized edit
        self.login('admin', 'default')        
        self.app.post('/editpost',data={
                            'id':post1.id,
                            'title':'editedtItle1',
                            'body':'editedbOdy1'})
        rv = self.app.get('/')
        assert 'editedtItle1' in rv.data
        assert 'editedbOdy1' in rv.data
        assert 'Tags:' in rv.data
        assert 'title2' in rv.data
        assert 'body2' in rv.data
        assert 'second' in rv.data
        assert 'not first' in rv.data
        assert 'title3' in rv.data
        assert 'body3' in rv.data
        assert 'third' in rv.data
        assert 'last' in rv.data
        assert 'title1' not in rv.data
        assert 'body1' not in rv.data
        # This should show for admin
        assert 'First' in rv.data
        # Non admin view
        self.logout()
        rv = self.app.get('/')
        assert 'editedtItle1' in rv.data
        assert 'editedbOdy1' in rv.data
        assert 'Tags:' in rv.data
        assert 'title2' in rv.data
        assert 'body2' in rv.data
        assert 'First' in rv.data
        assert 'second' in rv.data
        assert 'third' in rv.data
        assert 'last' in rv.data
        assert 'not first' in rv.data
        assert 'title3' in rv.data
        assert 'body3' in rv.data
        assert 'title1' not in rv.data
        assert 'body1' not in rv.data


if __name__ == '__main__':
    unittest.main()