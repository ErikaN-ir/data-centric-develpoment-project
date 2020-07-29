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
import pymongo

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
mongo = PyMongo(app)


# --------------------- UTIL FUNCTIONS AND CONTEXTS ---------------------
def is_logged_in():
    return session.get('user')

# @app.context_processor
# def format_poetry_writing(writing: str) -> str:
#     print(writing)
#     return writing.split('\n')


def format_poetry_writing(writing: str) -> str:
    print(writing)
    format_writing = writing.replace('\t', '        ')
    return format_writing.split('\n')


def something_like_buttons(work_id):
    print(work_id)
    if is_logged_in():
        all_likes = mongo.db.likes.find(
            {
                "work_id": work_id,
                "user": session["user"],
            })
        if all_likes.count() > 0:
            return "true"
        else:
            return "false"
    return "false"

@app.context_processor
def utility_processor():
    # Referenced from: https://stackoverflow.com/questions/6036082/call-a-python-function-from-jinja2
    return dict(
        format_poetry_writing=format_poetry_writing,
        something_like_buttons=something_like_buttons)

# --------------------- ENDPOINTS ---------------------


@app.route("/")
@app.route("/home")
def get_works():
    works = mongo.db.works.find().sort("_id", pymongo.DESCENDING)
    likes = mongo.db.likes.find()
    _genres = mongo.db.genres.find()
    genre_list = [genre for genre in _genres]
    _keys = mongo.db.keys.find()
    key_list = [key for key in _keys]
    return render_template(
        "works.html", works=works, likes=likes,
        genres=genre_list, keys=key_list)


# --------------------- SEARCH ---------------------
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    category = request.form.get("search-key")
    _keys = mongo.db.keys.find()
    key_list = [key for key in _keys]
    likes = mongo.db.likes.find()
    _genres = mongo.db.genres.find()
    genre_list = [genre for genre in _genres]
    try:
        works = mongo.db.works.find(
            {category: {"$regex": f'{query}', '$options': 'i'}})
    except Exception as e:
        print(e)
        flash("Couldn't find any works with that query.")
        return redirect(url_for("get_works"))
    return render_template(
        "works.html", works=works, likes=likes,
        genres=genre_list, keys=key_list)


@app.route("/filter_works", methods=["GET", "POST"])
def filter_works():
    works = mongo.db.works.find({
        "genre": request.form.get("genre_name")
    })
    genres = mongo.db.genres.find()
    genre_list = [genre for genre in genres]
    likes = mongo.db.likes.find()
    _keys = mongo.db.keys.find()
    key_list = [key for key in _keys]
    return render_template(
        "works.html", works=works, likes=likes,
        genres=genre_list, keys=key_list)


@app.route("/filter_profile", methods=["GET", "POST"])
def filter_profile():
    genre_form = {
        "genre": request.form.get("genre_name")
    }
    works = mongo.db.works
    results = works.find(genre_form)
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    genres = mongo.db.genres.find()
    genre_list = [genre for genre in genres]
    likes = mongo.db.likes.find()
    _keys = mongo.db.keys.find()
    key_list = [key for key in _keys]
    return render_template(
        "profile.html", username=username, works=results, likes=likes,
        genres=genre_list, keys=key_list)


@app.route("/filter_favourites", methods=["GET", "POST"])
def filter_favourites():
    genre_form = {
        "genre": request.form.get("genre_name")
    }
    works = mongo.db.works
    results = works.find(genre_form)
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    _genres = mongo.db.genres.find()
    genre_list = [genre for genre in _genres]
    likes = mongo.db.likes.find()
    _keys = mongo.db.keys.find()
    key_list = [key for key in _keys]
    return render_template(
        "favourites.html", username=username,
        works=results, genres=genre_list, likes=likes,
        keys=key_list)


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
        works = mongo.db.works.find(
        ).sort("_id", pymongo.DESCENDING)
        _genres = mongo.db.genres.find()
        genre_list = [genre for genre in _genres]
        return render_template(
            "profile.html", username=username, works=works, genres=genre_list)

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
        test = request.form.get("genre")
        print("genre submit =" + test)
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


@app.route("/view_work/<work_id>")
def view_work(work_id):
    # don't need login - edit/delete & like buttons only there if logged in
    try:
        the_work = mongo.db.works.find_one({"_id": ObjectId(work_id)})
        likes = mongo.db.likes.find()
            # {'work_id': {'$in': [work['_id'] for work in the_work]}})
    except bson.errors.InvalidId:
        flash("Work not found!", "error")
        return redirect(url_for("get_works"))
    except Exception:
        flash("An error occurred", "error")
        return redirect(url_for("get_works"))
    return render_template(
        'view_work.html', work=the_work, likes=likes)

# ----------------------- FAVOURITES/LIKES -----------------------


@app.route("/favourite/<work_id>")
def favourite(work_id):
    """
    Endpoint to add a work to favourites
    """
    if is_logged_in():
        try:
            favourite_info = {
                "user": session["user"],
                "work_id": ObjectId(work_id)
            }

            # mongo.db.user.update_one({'username': session['user'], {'work_ids': }})
            # {
            #     'username': '',
            #     'password': '',
            #     'work_ids': ['...', ..., ],
            # }

            upsert_info = mongo.db.likes.update(favourite_info, favourite_info, True)
            if upsert_info['updatedExisting']:
                flash("Already in favourites!", "info")
            else:
                flash("Added to favourites!", "info")
        except bson.errors.InvalidId:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))
        except Exception:
            flash("An error occurred", "error")
            return redirect(url_for("get_works"))
        return redirect(url_for('my_favourites'))
    return redirect(url_for("login"))


@app.route("/unfavourite/<work_id>")
def unfavourite(work_id):
    """
    Endpoint to remove a work to favourites
    """
    if is_logged_in():
        try:
            mongo.db.likes.remove({
                "user": session["user"],
                "work_id": ObjectId(work_id)
            })
            flash("Removed from favourites!", "info")
        except bson.errors.InvalidId:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))
        except Exception:
            flash("An error occurred", "error")
            return redirect(url_for("get_works"))
        return redirect(url_for('my_favourites'))
    return redirect(url_for("login"))


@app.route("/my_favourites", methods=["GET", "POST"])
def my_favourites():
    if is_logged_in():
        # If user is logged in
        # grab the user's username from db
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        # Filter the user's favourites
        likes = mongo.db.likes.find({'user': session['user']})

        # SELECT * FROM works
        # where id in (..., ...)
        works = mongo.db.works.find(
            {'_id': {'$in': [like['work_id'] for like in likes]}}
            ).sort("_id", pymongo.DESCENDING)
        genre_list = list(mongo.db.genres.find())
        return render_template(
            "favourites.html",
            username=username,
            works=works,
            likes=likes,
            genres=genre_list
        )

    # user isn't logged in
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
