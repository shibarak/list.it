from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, logout_user, login_required, current_user, LoginManager
from forms import LoginForm, UserForm
import shortuuid
import datetime
import config
import os

# ------------- Setup Flask app -----------------------------#
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
Bootstrap(app)

# ---------------------- setup SQL databases ----------------------#
if os.environ.get("DATABASE_URL") is None:
    app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///listit.db'
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

## configure tables

class ListItem(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    due_date = db.Column(db.String(250), nullable=True)
    complete = db.Column(db.Boolean)
    star = db.Column(db.Boolean)
    parent_list = relationship("List", back_populates="items")
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))


class List(db.Model):
    __tablename__ = "lists"
    id = db.Column(db.Integer, primary_key=True)
    url_key = db.Column(db.String(250), nullable=False, unique=True)
    name = db.Column(db.String(250), nullable=False)
    items = relationship("ListItem", back_populates="parent_list")
    user = relationship("User", back_populates="lists")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    lists = relationship("List", back_populates="user")

    __hash__ = object.__hash__

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return str(self.id)
        except AttributeError:
            raise NotImplementedError('No `id` attribute - override `get_id`')

    def __eq__(self, other):
        '''
        Checks the equality of two `UserMixin` objects using `get_id`.
        '''
        if isinstance(other, UserMixin):
            return self.get_id() == other.get_id()
        return NotImplemented

    def __ne__(self, other):
        '''
        Checks the inequality of two `UserMixin` objects using `get_id`.
        '''
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

# db.create_all()

#  Makes the "current_year" variable available in every template#
@app.context_processor
def inject_now():
    return {'current_year': datetime.date.today().strftime("%Y")}

# loads the current_user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


## root directory creats a new blank list and redirects to "home" #

@app.route("/", methods=["GET"])
def new_list():
    name = f"New List {datetime.date.today().strftime('%m/%d/%Y')}"
    # a pseudo random key for each list to be used in the URL instead of the ID
    url = shortuuid.ShortUUID().random(length=10)
    print(type(url))
    n_list = List(
        name=name,
        url_key=url
    )
    db.session.add(n_list)
    db.session.commit()
    return redirect(url_for("home", url_key=url))

# displays a new list om the home page
@app.route("/<url_key>", methods=["GET", "POST"])
def home(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    return render_template("newindex.html", list=list, url_key=url_key)

# takes the new list name and adds it to the database. returns home page with new name
@app.route("/name/<url_key>", methods=["POST"])
def new_name(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    lname = request.form['lname']
    list.name = lname
    db.session.commit()
    return redirect(url_for("home", url_key=list.url_key))

# takes new list item createb by user and adds it to the list
@app.route("/item/<url_key>", methods=["POST"])
def new_item(url_key):
    print(request.form)
    name = request.form['item']
    list = List.query.filter_by(url_key=url_key).first()
    new_item = ListItem(
        name=name,
        list_id=list.id
    )
    db.session.add(new_item)
    db.session.commit()
    return redirect(url_for("home", url_key=list.url_key))


@app.route("/date/<url_key>/<id>", methods=["POST"])
def new_date(id, url_key):
    print(request.form)
    due_date = request.form['due_date']
    item = ListItem.query.get(id)
    item.due_date = due_date
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))


@app.route("/complete/<url_key>/<id>", methods=["GET", "POST"])
def complete(url_key, id):
    item = ListItem.query.get(id)
    if item.complete:
        item.complete = False
    else:
        item.complete = True
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))


@app.route("/starred/<url_key>/<id>", methods=["GET", "POST"])
def starred(url_key, id):
    item = ListItem.query.get(id)
    if item.star:
        item.star = False
    else:
        item.star = True
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))


@app.route("/delete/<url_key>/<id>")
def delete_item(url_key, id):
    item_to_delete = ListItem.query.get(id)
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))


@app.route("/login/<url_key>", methods=["GET", "POST"])
def login(url_key):
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home', url_key=url_key))
            else:
                flash("Password incorrect. Please check password and try again")
                return render_template("login.html", form=form, url_key=url_key)
        else:
            flash("Email not found.")
            return render_template("login.html", form=form, url_key=url_key)
    return render_template("login.html", form=form, url_key=url_key)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("new_list"))

@app.route("/register/<url_key>", methods=["GET", "POST"])
def register(url_key):
    form = UserForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        if User.query.filter_by(email=email).first():
            flash("An account is already registered with this email address.")
            return render_template("register.html", form=form, url_key=url_key)
        name = form.name.data
        password = generate_password_hash(password=form.password.data,
                                          method="pbkdf2:sha256",
                                          salt_length=8)
        new_user = User(
            password=password,
            name=name,
            email=email
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home", url_key=url_key))
    return render_template("register.html", form=form, url_key=url_key)


@app.route("/save/<url_key>", methods=["GET", "POST"])
def save_list(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    list.user_id = current_user.id
    db.session.commit()
    return redirect(url_for('home', url_key=url_key))

@app.route("/user", methods=["GET", "POST"])
def user_page():
    return render_template("user.html")

@app.route("/delete-list/<url_key>")
def del_list(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    db.session.delete(list)
    db.session.commit()
    return redirect(url_for('user_page'))



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

