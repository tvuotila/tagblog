import os
import tagblog
import unittest
import tempfile

class TagblogTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, tagblog.app.config['DATABASE'] = tempfile.mkstemp()
        tagblog.app.config['TESTING'] = True
        self.app = tagblog.app.test_client()
        # Create test user
        tagblog.db.session.add(tagblog.User('admin', 'default'))
        tagblog.db.session.commit()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(tagblog.app.config['DATABASE'])

    def login(self, username, password):
        return self.app.post('/login', data=dict(
                            username=username,
                            password=password
                            ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_empty_db(self):
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
        rv = self.login('admin', 'default')
        # In
        assert 'Hello admin' in rv.data
        assert 'Logout' in rv.data
        # Not in
        assert 'Sign in' not in rv.data

        rv = self.logout()
        # In
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

        rv = self.login('adminx', 'default')
        # In
        assert 'invalid credentials' in rv.data
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

        rv = self.login('admin', 'defaultx')
        # In
        assert 'invalid credentials' in rv.data
        assert 'Sign in' in rv.data
        # Not in
        assert 'Hello' not in rv.data
        assert 'Logout' not in rv.data

if __name__ == '__main__':
    unittest.main()