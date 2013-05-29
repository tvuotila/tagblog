import os
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:////C:/tmp/test.db')