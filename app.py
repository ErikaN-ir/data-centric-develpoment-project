import os

import bson
from flask import (
    Flask, flash,
    render_template,
    redirect, request,
    session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
mongo = PyMongo(app)


def is_logged_in():
    return session.get('user')


@app.route("/")
@app.route("/home")
def get_works():
    works = mongo.db.works.find()
    _genres = mongo.db.genres.find()
    genre_list = [genre for genre in _genres]
    return render_template("works.html", works=works, genres=genre_list)


@app.route("/search", methods=["GET", "POST"])
def search1():
    query = request.form.get("query")
    try:
        works = list(mongo.db.works.find(
            {"writing": {"$regex": f'/{query}$/'}}))
    except Exception:
        flash("Couldn't find any works with that query.")
        return redirect(url_for("get_works"))
    return render_template("search.html", works=works)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    works = mongo.db.works.find({"author": query})
    return render_template("work.html", works=works)


@app.route("/filter", methods=["GET", "POST"])
def filter():
    genre = {
        "genre": request.form.get("genre_name")
        }
    works = mongo.db.works
    results = works.find(genre)
    return render_template("works.html", works=results)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists", 'error')
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }

        mongo.db.users.insert_one(register)
        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")))
                return redirect(url_for(
                    "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password", "error")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if is_logged_in():  # If user is logged in
        # grab the user's username from db
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        works = mongo.db.works.find()
        return render_template(
            "profile.html", username=username, works=works)

    # user isn't logged in
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookies
    flash("You have been logged out", "success")
    # Added None default so any other attempts
    # to logout by a non-logged in user
    # will not throw an error
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/add_work")
def add_work():
    if is_logged_in():
        _genres = mongo.db.genres.find()
        genre_list = [genre for genre in _genres]
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        return render_template(
            'create.html', genres=genre_list, username=username)
    return redirect(url_for("login"))


@app.route("/insert_work", methods=['POST'])
def insert_work():
    works = mongo.db.works
    submit = {
            "author": session["user"],
            "title": request.form.get("title"),
            "genre": request.form.get("genre_name"),
            "writing": request.form.get("writing")
        }
    works.insert_one(submit)
    return redirect(url_for('profile'))


@app.route("/delete/<work_id>")
def delete_work(work_id):
    if is_logged_in():
        try:
            mongo.db.works.remove({"_id": ObjectId(work_id)})
        except Exception:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))

        flash("Work Successfully Deleted", "success")
        return redirect(url_for("get_works"))
    return redirect(url_for("login"))


@app.route("/edit_work/<work_id>")
def edit_work(work_id):
    if is_logged_in():
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        try:
            the_work = mongo.db.works.find_one({"_id": ObjectId(work_id)})
            all_genres = mongo.db.genres.find()
        except bson.errors.InvalidId:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))
        except Exception:
            flash("An error occurred", "error")
            return redirect(url_for("get_works"))
        return render_template(
            'edit_work.html', work=the_work,
            genres=all_genres, username=username)

    return redirect(url_for("login"))


@app.route("/update_work/<work_id>", methods=["POST"])
def update_work(work_id):
    # A decorator could've been used for this login check functionality
    if is_logged_in():
        submit = {
            "author": session["user"],
            "title": request.form.get("title"),
            "genre": request.form.get("genre"),
            "writing": request.form.get("writing")
        }

        try:
            mongo.db.works.update_one(
                {"_id": ObjectId(work_id)}, {'$set': submit})
        except bson.errors.InvalidId:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))
        except Exception:
            flash("An error occurred", "error")
            return redirect(url_for("get_works"))

        flash("Work Successfully Updated", "success")
        return redirect(url_for("profile"))

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
