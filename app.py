#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime

from flask import Flask, session, render_template, request, redirect, url_for, make_response

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv(override=True)  # take environment variables from .env.

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")  # Needed for session management

# # turn on debugging if in development mode
app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    # sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


# set up the routes


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    return render_template("index.html")


@app.route("/read")
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    sort_field = request.args.get('sort', 'created_at')  # Default sort is by 'created_at'
    sort_order = request.args.get('order', 'desc')  # Default order is descending
    search_query = request.args.get('search', '')

    next_order = 'asc' if sort_order == 'desc' else 'desc'
    mongo_sort_order = -1 if sort_order == 'desc' else 1

    query = {"name": {"$regex": search_query, "$options": "i"}} if search_query else {}
    
    # Execute the query with sorting
    docs = db.exampleapp.find(query).sort(sort_field, mongo_sort_order)

    return render_template(
        "read.html",
        docs=docs,
        next_order=next_order,
        sort_field=sort_field,
        search_query=search_query
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    """
    Route for GET and POST requests to the create page.
    Creates new recipe.
    """
    if request.method == "POST":
        navigation = request.form.get('navigation', 'next')
        step = request.form.get('step', '1')
        
        if navigation == 'next':
            step = str(int(step) + 1)
        else:  # Handle 'prev' navigation
            step = str(int(step) - 1)
        
        # Updating session data only if moving forward
        if navigation == 'next':
            session['base'] = request.form.get('base', session.get('base', ''))
            session['flavor'] = request.form.get('flavor', session.get('flavor', ''))
            session['nutrition'] = request.form.get('nutrition', session.get('nutrition', ''))
            session['texture'] = request.form.get('texture', session.get('texture', ''))
            session['name'] = request.form.get('name', session.get('name', ''))

        if step == '6':  # After final step
            doc = {
                "base": session['base'],
                "flavor": session['flavor'],
                "nutrition": session['nutrition'],
                "texture": session['texture'],
                "name": session['name'],
                "created_at": datetime.datetime.utcnow()
            }
            db.exampleapp.insert_one(doc)  # insert a new document
            session.clear()  # Clear the session after saving to DB
            return redirect(url_for("read"))
        else:
            return redirect(url_for("create", step=step))

    step = request.args.get('step', '1')
    return render_template(f"create_step{step}.html", data=session)


# @app.route("/edit/<mongoid>", methods=["GET"])
# def edit(mongoid):
#     """
#     Initialize the editing process by loading the document and storing its data in the session.
#     """
#     doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
#     session['edit_data'] = doc  # Store the document data in the session
#     return redirect(url_for("edit_step", mongoid=mongoid, step=1))

@app.route("/edit/<mongoid>", methods=["GET", "POST"])
def edit(mongoid):
    """
    Handle each step of the edit process.
    """
    if request.method == "POST":
        navigation = request.form.get('navigation', 'next')
        step = request.form.get('step', '1')
        
        if navigation == 'next':
            step = str(int(step) + 1)
        else:  # Handle 'prev' navigation
            step = str(int(step) - 1)
        
        # Updating session data only if moving forward
        if navigation == 'next':
            session['base'] = request.form.get('base', session.get('base', ''))
            session['flavor'] = request.form.get('flavor', session.get('flavor', ''))
            session['nutrition'] = request.form.get('nutrition', session.get('nutrition', ''))
            session['texture'] = request.form.get('texture', session.get('texture', ''))
            session['name'] = request.form.get('name', session.get('name', ''))

        if step == '6':  # After final step
            doc = {
                "base": session['base'],
                "flavor": session['flavor'],
                "nutrition": session['nutrition'],
                "texture": session['texture'],
                "name": session['name'],
                "created_at": datetime.datetime.utcnow()
            }
            # Update the database with the new data
            db.exampleapp.update_one(
                {"_id": ObjectId(mongoid)}, {"$set": doc}
            )
            session.clear()  # Clear the session after saving to DB
            return redirect(url_for("read"))
        else:
            return redirect(url_for("edit", step=step, mongoid=mongoid))

    step = request.args.get('step', '1')
    old_data = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    return render_template(f"edit_step{step}.html", old_data=old_data, data=session, mongoid=mongoid)


@app.route("/delete/<mongoid>")
def delete(mongoid):
    """
    Route for GET requests to the delete page.
    Deletes the specified record from the database, and then redirects the browser to the read page.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be deleted.
    """
    db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
    return redirect(
        url_for("read")
    )  # tell the web browser to make a request for the /read route.


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response(f"output: {pull_output}", 200)
    response.mimetype = "text/plain"
    return response


@app.errorhandler(Exception)
def handle_error(err):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=err)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
