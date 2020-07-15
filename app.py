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


def is_logged_in():
    return session.get('user')


@app.route("/")
@app.route("/home")
def get_works():
    works = mongo.db.works.find()
    return render_template("works.html", works=works)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    try:
        works = list(mongo.db.works.find(
            {"writing": {"$regex": f'/{query}$/'}}))
    except Exception:
        flash("Couldn't find any works with that query.")
        return redirect(url_for("home"))
    return render_template("works.html", works=works)


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
        return render_template("profile.html", username=username)

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


@app.route("/add_work", methods=["GET", "POST"])
def add_work():
    if is_logged_in():
        if request.method == "POST":
            work = {
                "author": session["user"],
                "title": request.form.get("title"),
                "genre": request.form.get("genre"),
                "writing": request.form.get("writing")
            }
            mongo.db.works.insert_one(work)
            flash("Work Successfully Published!", "success")
            return redirect(url_for("get_works"))
        genres = mongo.db.genres.find().sort("genre_name", pymongo.ASCENDING)
        return render_template("create.html", genres=genres)
    return redirect(url_for("login"))


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


@app.route("/edit_work/<work_id>", methods=["GET", "POST"])
def edit_work(work_id):
    # A decorator could've been used for this login check functionality
    if is_logged_in():
        if request.method == "POST":
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
            return redirect(url_for("get_works"))

        # GET request
        try:
            work = mongo.db.works.find_one({"_id": ObjectId(work_id)})
        except bson.errors.InvalidId:
            flash("Work not found!", "error")
            return redirect(url_for("get_works"))
        except Exception:
            flash("An error occurred", "error")
            return redirect(url_for("get_works"))

        genres = mongo.db.genres.find().sort("genre_name", pymongo.ASCENDING)
        return render_template("edit_work.html", work=work, genres=genres)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
