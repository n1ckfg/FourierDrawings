import secrets
from os import environ, path, walk

from flask import Flask
from flask_bootstrap import Bootstrap

from fourier import fourier_blueprint



def create_app():
    flask_app = Flask(__name__)
    # Serve Bootstrap and jQuery from Flask-Bootstrap's bundled copies instead of a CDN.
    flask_app.config['BOOTSTRAP_SERVE_LOCAL'] = True
    Bootstrap(flask_app)

    # Signs the session cookie and the CSRF tokens, so it must stay secret.
    flask_app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
    if not flask_app.config['SECRET_KEY']:
        flask_app.logger.warning('SECRET_KEY is not set; using a random key. Set it when running '
                                 'several worker processes, or their CSRF tokens will not match.')
        flask_app.config['SECRET_KEY'] = secrets.token_hex(32)

    flask_app.register_blueprint(fourier_blueprint)

    return flask_app


app = create_app()

if __name__ == '__main__':
    extra_dirs = ['templates', 'static']
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in walk(extra_dir):
            for filename in files:
                filename = path.join(dirname, filename)
                if path.isfile(filename):
                    extra_files.append(filename)

    app.run(host="localhost", port=int(environ.get('PORT', 8002)), debug=True, extra_files=extra_files)
