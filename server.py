"""
Flask application requirements:
Template must reside in templates folder
Static file must reside in static folder
Database must reside in instance folder
"""

from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email
from flask_ckeditor import CKEditor, CKEditorField
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash


# Create Flask application
app = Flask(__name__)
# Add csrf protection
app.secret_key = "any-string-you-want-just-keep-it-secret"
# Initialise SQLAlchemy, Bootstrap-Flask, CKEditor, Flask-Login extensions
# and configure Flask application for extensions
db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///new-books-collection.db"
db.init_app(app)
Bootstrap5(app)
ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)


# Example of configuring data table with SQLAlchemy
class Book(db.Model):
    __tablename__ = "book"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    author = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=False)

    # Create dictionary of data table columns
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def __repr__(self):
        return f'<Book {self.title}>'


# Example of configuring data table that inherits UserMixin
# https://flask-login.readthedocs.io/en/latest/#your-user-class
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


# Create data tables in database
with app.app_context():
    db.create_all()


# Example of creating decorator function
def make_bold(func):
    def wrapper_func():
        text = func()
        return f"<b>{text}</b>"
    return wrapper_func


# Example of creating child class of WTForms
class LoginForm(FlaskForm):
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=3)])
    message = CKEditorField("Message", validators=[DataRequired()])
    submit = SubmitField(label="Log In")


# Create a Flask-Login user_loader callback (not sure what this is)
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


"""
Examples of Flask web application pages and
examples of SQLAlchemy CRUD operations and Flask-Login user sessions
"""


# Example use of additional decorator function and in-line CSS
@app.route("/", methods=["GET"])
@make_bold
def home_page():
    return "<p style='text-align: center'>Hello, World!</p>"


# Example use of URL paths
@app.route('/<int:guess_path>')
def page_num(guess_path):
    return f"<h1>This is page number {guess_path}</h1>"


# Example use of rendering HTML template and jinja
@app.route("/boiler")
def boiler_page():
    number = 9
    word = 'string of text'
    list = [1, 2, 3, 4, 5]
    return render_template("boiler.html", number=number, word=word, list=list)


# Example use of dynamic HTML page
@app.route('/books')
def books_page():
    # Read all records from data table
    result = db.session.execute(db.select(Book).order_by(Book.title))
    # Return all elements from records
    all_books = result.scalars()
    return render_template("books.html", books=all_books, current_user=current_user)


# Example use of HTML forms
@app.route('/register', methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        new_email = request.form['email']
        new_name = request.form['name']
        new_password = request.form['password']
        # Hash and salt the password entered by user
        hash_and_salted_password = generate_password_hash(
            new_password,
            method='pbkdf2:sha256',
            salt_length=8
        )
        # Create record in data table
        # noinspection PyArgumentList
        new_user = User(
            email=new_email,
            name=new_name,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # Log in and store user in session as: current_user
        login_user(new_user)
        return redirect(url_for('books_page'))
    return render_template("register.html")


# Example use of URL arguments, redirect and url_for
@app.route("/edit", methods=["GET", "POST"])
# Restrict route to logged-in users
@login_required
def edit_page():
    if request.method == "POST":
        # Update record in data table
        book_id = request.form["id"]
        book_to_update = db.get_or_404(Book, book_id)
        book_to_update.rating = request.form["rating"]
        db.session.commit()
        return redirect(url_for('books_page'))
    book_id = request.args['id']
    # Read record from data table: Option 1
    book_selected = db.get_or_404(Book, book_id)
    return render_template("edit.html", book=book_selected, current_user=current_user)


# Example use of WTForms
@app.route("/login", methods=["GET", "POST"])
def login_page():
    login_form = LoginForm(
        message="This is a default message"
    )
    if login_form.validate_on_submit():
        form_email = login_form.email.data
        form_password = login_form.password.data
        # Read record from data table: Option 2
        result = db.session.execute(db.select(User).where(User.email == form_email))
        retrieved_user = result.scalar()
        # Example use of Flask Flash messages
        if retrieved_user:
            # Check entered password hashed against stored password hash
            if check_password_hash(retrieved_user.password, form_password):
                login_user(retrieved_user)
                return render_template("success.html", message="Login is successful")
            else:
                flash("Password incorrect, please try again.")
        else:
            flash("That email does not exist, please try again.")
    return render_template('login.html', form=login_form, is_edit=True)


# Log out current user from session
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template("success.html", message="Logout is successful")


# Example use of jsonify with GET
@app.route("/query", methods=["GET"])
def query_url():
    selected_author = "Meauthor"
    result = db.session.execute(db.select(Book).where(Book.author == selected_author))
    all_books = result.scalars()
    if all_books:
        return jsonify(books=[book.to_dict() for book in all_books]), 200
    else:
        return jsonify(error={"Not Found": "Sorry, we don't have a book by that author."}), 404


# Example use of jsonify with PATCH and URL paths and URL arguments
@app.route("/edit-uri/<int:book_id>", methods=["PATCH"])
def edit_api_uri(book_id):
    new_rating = request.args.get("new_rating")
    book = db.session.get(Book, book_id)
    if book:
        book.rating = new_rating
        db.session.commit()
        return jsonify(response={"success": "Successfully updated the rating."}), 200
    else:
        return jsonify(error={"Not Found": "Sorry a book with that id was not found in the database."}), 404


# Run Flask application server
if __name__ == "__main__":
    app.run(debug=True)


# # Perform CRUD operations with SQLAlchemy
# # Delete a record
# with app.app_context():
#     book_id = 19
#     book_to_delete = db.get_or_404(Book, book_id)
#     db.session.delete(book_to_delete)
#     db.session.commit()

# # Create database, table and record with built-in SQLite
# db = sqlite3.connect("./instance/books-collection.db")
# cursor = db.cursor()

# cursor.execute(
#     "CREATE TABLE books ("
#     "id INTEGER PRIMARY KEY, "
#     "title varchar(250) NOT NULL UNIQUE, "
#     "author varchar(250) NOT NULL, "
#     "rating FLOAT NOT NULL"
#     ")"
# )

# cursor.execute(
#     "INSERT INTO books VALUES("
#     "1, 'Harry Potter', 'J. K. Rowling', '9.3'"
#     ")"
# )
# db.commit()
