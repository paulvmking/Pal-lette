import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from flask_paginate import Pagination, get_page_args
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


recipes = mongo.db.recipes.find()

PER_PAGE = 4


def paginated(recipes):
    page, per_page, offset = get_page_args(
        page_parameter='page', per_page_parameter='per_page')
    offset = page * PER_PAGE - PER_PAGE
    return recipes[offset: offset + PER_PAGE]


def pagination_args(recipes):
    page, per_page, offset = get_page_args(
        page_parameter='page', per_page_parameter='per_page')
    total = recipes.count()
    return Pagination(page=page, per_page=PER_PAGE, total=total)


@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    recipes = mongo.db.recipes.find().sort("_id", -1)
    recipes_paginated = paginated(recipes)
    pagination = pagination_args(recipes)
    return render_template("recipes.html", recipes=recipes,
                           recipe_paginated=recipes_paginated,
                           pagination=pagination,)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Sorry that username already exists.")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:

            if check_password_hash(
               existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")))
                return redirect(url_for(
                    "profile", username=session["user"]))
            else:
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):

    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    users = list(mongo.db.users.find())
    recipes = list(mongo.db.recipes.find())

    if session["user"]:
        return render_template(
            "profile.html", username=username, users=users,
            recipes=recipes)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        is_vegan = "on" if request.form.get("is_vegan") else "off"
        recipe = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "serves": request.form.get("serves"),
            "ingredients": request.form.get("ingredients"),
            "directions": request.form.get("directions"),
            "is_vegan": is_vegan,
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        is_vegan = "on" if request.form.get("is_vegan") else "off"
        recipe_edit = {
            "category_name": request.form.get("category_name"),
            "recipe_name": request.form.get("recipe_name"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "serves": request.form.get("serves"),
            "ingredients": request.form.get("ingredients"),
            "directions": request.form.get("directions"),
            "is_vegan": is_vegan,
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, recipe_edit)
        flash("Recipe Updated Successfully")

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template(
        "edit_recipe.html", recipe=recipe, categories=categories)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Deleted Successfully")
    return redirect(url_for("get_recipes"))


@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


@app.route("/view_recipe/<recipe_id>", methods=["GET", "POST"])
def view_recipe(recipe_id):

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find()
    return render_template("view_recipe.html", recipe=recipe,
                           categories=categories)


@app.route("/favourite_recipe/<recipe_id>", methods=["GET", "POST"])
def favourite_recipe(recipe_id):
    mongo.db.users.find_one_and_update(
        {"username": session["user"].lower()},
        {"$push": {"favourite_recipes": ObjectId(recipe_id)}})
    flash("Recipe added to favourites!")
    return redirect(url_for("get_recipes"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
