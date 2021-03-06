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
# gets user info
def is_logged_in():
    return session.get('user')


# general filter function for home, profile and favourites filter forms
def get_filter_data(request, filter_criteria: dict):
    if not request.form.get("genre_name"):
        flash("Please enter a genre when filtering.", 'error')
        return redirect(url_for("get_works"))
    # works is a collection of writing info (keys: author, genre, title, content)
    # genres is a collection of all the genre forms (key(s): genre_name)
    # likes is a collection of all the works of other users that have been liked by the user
    # likes (key(s): user, work_id)
    # keys is a collection of the searchable keys in the works collection eg. author (key(s): key_name)
    works = mongo.db.works.find(filter_criteria)
    genre_list = mongo.db.genres.find()
    likes = mongo.db.likes.find()
    key_list = mongo.db.keys.find()

    return dict(works=works, likes=likes,
                genres=genre_list, keys=key_list)


# formats the writing content for html rendering (tabs nad new lines)
def format_poetry_writing(writing: str) -> str:
    print(writing)
    format_writing = writing.replace('\t', '       ')
    return format_writing.split('\n')


# determine whether like (favourite) or unlike (unfavourite) button displays
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

# ------------------------- ENDPOINTS -------------------------
# -------------------------- HOME -----------------------------


@app.route("/")
@app.route("/home")
# displays works from all the app users
# don't need to be logged in to view works
def get_works():
    works = mongo.db.works.find().sort("_id", pymongo.DESCENDING)
    likes = mongo.db.likes.find()
    genre_list = mongo.db.genres.find()
    key_list = mongo.db.keys.find()
    return render_template(
        "works.html", works=works, likes=likes,
        genres=genre_list, keys=key_list)


# --------------------- SEARCH ----------------------------
# search function for queries in authors, titles, content
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    key_list = mongo.db.keys.find()
    likes = mongo.db.likes.find()
    genre_list = mongo.db.genres.find()
    try:
        category = request.form.get("search-key")
        if not category:
            raise Exception("Category cannot be None")
        works = mongo.db.works.find(
            {category.lower(): {"$regex": f'{query}', '$options': 'i'}})
        return render_template("works.html", works=works or [], likes=likes,
                               genres=genre_list, keys=key_list)
    except Exception as e:
        print(e)
        flash("Couldn't find any works with that query.", 'error')
    return redirect(url_for("get_works"))

# -------------------------- FILTERS -----------------------------


@app.route("/filter_works", methods=["GET", "POST"])
# filters works from all users on home page
def filter_works():
    data = get_filter_data(request, {"genre": request.form.get("genre_name")})
    if not isinstance(data, dict):
        return data
    return render_template("works.html", **data)


@app.route("/filter_profile", methods=["GET", "POST"])
# filters user's works by genre displayed on profile.html
def filter_profile():
    work_filter = {
        "genre": request.form.get("genre_name"),
        "author": session["user"].lower()
    }

    data = get_filter_data(request, work_filter)
    if not isinstance(data, dict):
        return data

    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    return render_template(
        "profile.html", username=username, **data)


@app.route("/filter_favourites", methods=["GET", "POST"])
# filters works by genre displayed in favourites collection
def filter_favourites():
    data = get_filter_data(request, {"genre": request.form.get("genre_name")})
    if not isinstance(data, dict):
        return data
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    return render_template(
        "favourites.html", username=username, **data)

# -------------------------- REGISTER -----------------------------


@app.route("/register", methods=["GET", "POST"])
# register user
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
        flash("Registration Successful!", 'info')
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")

# -------------------------- LOGIN -----------------------------


@app.route("/login", methods=["GET", "POST"])
# login user
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
                    request.form.get("username")), "info")
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

# -------------------------- PROFILE -----------------------------


@app.route("/profile", methods=["GET", "POST"])
# displays user's own work and provides genres for filter
def profile():
    if is_logged_in():  # If user is logged in
        # grab the user's username from db
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        works = mongo.db.works.find(
        ).sort("_id", pymongo.DESCENDING)
        genre_list = mongo.db.genres.find()
        return render_template(
            "profile.html", username=username, works=works, genres=genre_list)

    # user isn't logged in
    return redirect(url_for("login"))


# -------------------------- LOGOUT -----------------------------


@app.route("/logout")
# logout function
def logout():
    # remove user from session cookies
    flash("You have been logged out", "info")
    # Added None default so any other attempts
    # to logout by a non-logged in user
    # will not throw an error
    session.pop("user", None)
    return redirect(url_for("login"))


# -------------------------- CREATE -----------------------------


@app.route("/add_work")
# redirects to create.html if logged in
def add_work():
    if is_logged_in():
        genre_list = mongo.db.genres.find()
        username = mongo.db.users.find_one(
            {"username": session["user"]})["username"]
        return render_template(
            'create.html', genres=genre_list, username=username)
    return redirect(url_for("login"))


@app.route("/insert_work", methods=['POST'])
# adds work to db
def insert_work():
    submit = {
        "author": session["user"],
        "title": request.form.get("title"),
        "genre": request.form.get("genre_name"),
        "writing": request.form.get("writing")
    }
    mongo.db.works.insert_one(submit)
    return redirect(url_for('profile'))

# -------------------------- DELETE -----------------------------


@app.route("/delete/<work_id>")
# removes work form db
def delete_work(work_id):
    if is_logged_in():
        try:
            mongo.db.works.remove({"_id": ObjectId(work_id)})
        except Exception:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))

        flash("Work Successfully Deleted", "info")
        return redirect(url_for("get_works"))
    return redirect(url_for("login"))

# -------------------------- EDIT -----------------------------


@app.route("/edit_work/<work_id>")
# opens the relevant work for editing
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
# updates changes to the db
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

        flash("Work Successfully Updated", "info")
        return redirect(url_for("profile"))

    return redirect(url_for("login"))

# -------------------------- READ/VIEW -----------------------------


@app.route("/view_work/<work_id>")
# opens individual work in browser
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
# adds work to user's "liked" collection/list
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

            # This was an alternative way to structure the collections
            # mongo.db.user.update_one({'username': session['user'], {'work_ids': }})
            # {
            #     'username': '',
            #     'password': '',
            #     'work_ids': ['...', ..., ],
            # }

            upsert_info = mongo.db.likes.update(
                favourite_info, favourite_info, True)
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
# removes work from user's liked list
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
# View all works (of other users) that this user "liked"
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
            debug=False)
