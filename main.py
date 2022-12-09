from flask import Flask, request, redirect, render_template, session, url_for
from urllib.parse import quote_plus, urlencode
from flask_sqlalchemy import SQLAlchemy
from bible import bibleBenny
from os import environ as env
from dotenv import find_dotenv, load_dotenv
from authlib.integrations.flask_client import OAuth

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)

app.secret_key = env.get("APP_SECRET_KEY")
oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///testdb.sqlite' # os.getenv('SQUALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)

class Commentary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    author_id = db.Column(db.String, nullable=False)

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, nullable=False)
    commentary = db.Column(db.Integer, db.ForeignKey('commentary.id'), nullable=False)
    uninspired_html = db.Column(db.String)
    book = db.Column(db.String, nullable=False)
    start_chapter = db.Column(db.Integer, nullable=False)
    start_verse = db.Column(db.Integer, nullable=False)
    end_chapter = db.Column(db.Integer)
    end_verse = db.Column(db.Integer)

class BibleCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block = db.Column(db.Integer, db.ForeignKey('block.id'), nullable=False)
    bible = db.Column(db.String, nullable=False)
    text = db.Column(db.String, nullable=False)

class BibleCopyright(db.Model):
    bible = db.Column(db.String, primary_key=True)
    copyright = db.Column(db.String, nullable=False)

with app.app_context():
    db.create_all()


def get_verses(block, bible):
    with app.app_context():
        cache = BibleCache.query.filter_by(block=block.id, bible=bible).first()
        if cache:
            return cache.text
        else:
            text, copyright = bibleBenny.get_verses(bible, [
                block.__dict__
            ])
            text = render_template('text_passage.html', passage=text[0])
            copyright = render_template('text_copyright.html', copyright=copyright)
            db.session.add(BibleCache(
                block = block.id,
                bible = bible,
                text = text
            ))
            db.session.merge(BibleCopyright(
                bible = bible,
                copyright = copyright
            ))
            db.session.commit()
            return text

def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

@app.route('/commentary/<int:commentary_id>/<bible>')
def show_commentary(commentary_id, bible):
    with app.app_context():
        commentary = Commentary.query.get(commentary_id)
        blocks = Block.query.filter_by(commentary=commentary_id).order_by(Block.order.desc()).all()
        passages = [get_verses(block, bible) for block in blocks]
        copyright = BibleCopyright.query.get(bible).copyright
        print(passages)
        return render_template('commentary.html', commentary=commentary, blocks_passages = zip(blocks, passages), copyright=copyright)

ARG_DELETE = 'delete'

@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if user:
        with app.app_context():
            if ARG_DELETE in request.args:
                to_delete = Commentary.get(request.args.get(ARG_DELETE))
                if to_delete.author_id == user.userinfo.sub:
                    db.session.delete(to_delete)
                for block in Block.query.filter_by(commentary=to_delete.id):
                    db.session.delete(block)
                db.session.commit()
            commentaries = Commentary.query.filter_by(author_id=user.userinfo.sub)
            return render_template('dashboard.html', user=user, commentaries=commentaries)
    else:
        return redirect("/")

if __name__ == "__main__":
    app.run()