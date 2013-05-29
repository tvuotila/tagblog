from flask import Flask, render_template, Markup, abort, redirect, url_for, request

app = Flask(__name__)
app.config.from_pyfile('settings.py')


@app.route('/')
def helloworld():
    return render_template('hello.html')


if __name__ == '__main__':
    app.run(debug=True)