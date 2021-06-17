import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from flask_paginate import Pagination, get_page_parameter
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

# Configuration #
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# Pagination #
recipes = mongo.db.recipes.find()

PER_PAGE = 4


def paginated(recipes, page):
    offset = page * PER_PAGE - PER_PAGE
    paginated_recipes = recipes[offset: offset + PER_PAGE]
    pagination = Pagination(page=page, per_page=PER_PAGE, total=len(recipes))
    return [
        paginated_recipes,
        pagination
    ]


# Homepage #
@app.route("/")
@app.route("/get_homepage")
def get_homepage():
    return render_template("index.html")


# Main recipes page #
@app.route("/get_recipes")
def get_recipes():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    recipes = list(mongo.db.recipes.find().sort("_id", -1))
    pagination_obj = paginated(recipes, page)
    paginated_recipes = pagination_obj[0]
    pagination = pagination_obj[1]
    return render_template("recipes.html", recipes=paginated_recipes,
                           recipe_paginated=paginated_recipes,
                           pagination=pagination)


# Search functionality #
@app.route("/search", methods=["GET", "POST"])
def search():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    pagination_obj = paginated(recipes, page)
    paginated_recipes = pagination_obj[0]
    pagination = pagination_obj[1]
    categories = mongo.db.categories.find()
    return render_template("recipes.html", recipes=recipes,
                           total=len(recipes), categories=categories,
                           recipe_paginated=paginated_recipes,
                           pagination=pagination,
                           title="Search Result", search=True)


# Registration page #
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


# Log in page #
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


# User profile page #
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    users = list(mongo.db.users.find())
    recipes = list(mongo.db.recipes.find())
    favourite_recipes = mongo.db.users.find_one(
                {"username": session["user"]})["favourite_recipes"]
    # Favourite recipe display functionality #
    favourites = []
    for recipe in favourite_recipes:
        favourites.append(mongo.db.recipes.find_one({"_id": recipe}))
    if session["user"]:
        return render_template(
            "profile.html", username=username, users=users,
            recipes=recipes, favourites=favourites)

    return redirect(url_for("login"))


# Logout functionality #
@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


# Create recipe functionality and page #
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
            "image": request.form.get("image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_recipe.html", categories=categories)


# Edit recipe functionality and page #
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
            "image": request.form.get("image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, recipe_edit)
        flash("Recipe Updated Successfully")

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template(
        "edit_recipe.html", recipe=recipe, categories=categories)


# Delete recipe functionality #
@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    list(mongo.db.users.find(
        {"favourite_recipes": ObjectId(recipe_id)}))
    mongo.db.users.find_one_and_update(
            {"username": session["user"].lower()},
            {"$pull": {"favourite_recipes": ObjectId(recipe_id)}})
    flash("Recipe Deleted Successfully")
    return redirect(url_for("get_recipes"))


# Get categories for admin functionality #
@app.route("/get_categories")
def get_categories():
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    if username == "admin":
        categories = list(mongo.db.categories.find().sort("category_name", 1))
        return render_template("categories.html", categories=categories)
    else:
        flash("You are not authorised to view that page!")
        return redirect(url_for("profile", username=session["user"]))


# Add categories for admin functionality #
@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    if username == "admin":
        if request.method == "POST":
            category = {
                "category_name": request.form.get("category_name")
            }
            mongo.db.categories.insert_one(category)
            flash("New Category Added")
            return redirect(url_for("get_categories"))

        return render_template("add_category.html")
    else:
        flash("You are not authorised to view that page!")
        return redirect(url_for("profile", username=session["user"]))


# Edit categories for admin functionality #
@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    if username == "admin":
        if request.method == "POST":
            submit = {
                "category_name": request.form.get("category_name")
            }
            mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
            flash("Category has been successfully updated")
            return redirect(url_for("get_categories"))

        category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
        return render_template("edit_category.html", category=category)
    else:
        flash("You are not authorised to view that page!")
        return redirect(url_for("profile", username=session["user"]))


# Delete categories for admin functionality #
@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    if username == "admin":
        mongo.db.categories.remove({"_id": ObjectId(category_id)})
        flash("Category has been successfully deleted")
        return redirect(url_for("get_categories"))
    else:
        flash("You are not authorised to view that page!")
        return redirect(url_for("profile", username=session["user"]))


# View single recipe #
@app.route("/view_recipe/<recipe_id>", methods=["GET", "POST"])
def view_recipe(recipe_id):

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find()
    return render_template("view_recipe.html", recipe=recipe,
                           categories=categories)


# Add recipe to favourites array in DB #
@app.route("/favourite_recipe/<recipe_id>", methods=["GET", "POST"])
def favourite_recipe(recipe_id):
    favourites = mongo.db.users.find(
        {"favourite_recipes": ObjectId(recipe_id)})
    favourite = mongo.db.users.find_one(
        {"favourite_recipes": ObjectId(recipe_id)})
    if favourite in favourites:
        flash("This recipe is already in your favourites!")
        return redirect(url_for("get_recipes"))
    else:
        mongo.db.users.find_one_and_update(
            {"username": session["user"].lower()},
            {"$push": {"favourite_recipes": ObjectId(recipe_id)}})
        flash("Recipe added to your favourites!")
        return redirect(url_for("profile", username=session["user"]))


# Remove or delete recipe from favourites functionality #
@app.route("/remove_recipe/<recipe_id>", methods=["GET", "POST"])
def remove_recipe(recipe_id):
    favourites = list(mongo.db.users.find(
        {"favourite_recipes": ObjectId(recipe_id)}))
    if len(favourites) <= 0:
        flash("This recipe is not in your favourites!")
        return redirect(url_for("get_recipes"))
    else:
        mongo.db.users.find_one_and_update(
            {"username": session["user"].lower()},
            {"$pull": {"favourite_recipes": ObjectId(recipe_id)}})
        flash("Recipe removed from your favourites!")
        return redirect(url_for("profile", username=session["user"]))


# Run the application #
if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
