from flask import Flask, render_template, Markup, abort, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('settings.py')
db = SQLAlchemy(app)

# Class for testing database connection
# Contains number of visits to a site.
class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)

# Create database
db.create_all()

# HelloWorld for testing site
@app.route('/')
def helloworld():
    visit = Visitor.query.first()
    if visit == None:
        visit = Visitor()
        visit.number = 0
    visit.number = visit.number + 1
    db.session.add(visit)
    db.session.commit()
    return render_template('hello.html', visitors=visit.number)


if __name__ == '__main__':
    app.run(debug=True)