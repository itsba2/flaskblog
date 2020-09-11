from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Please log in to enter Control Panel!","danger")
            return redirect(url_for("login"))
    return decorated_function


class RegisterForm(Form):
    name = StringField("Full Name",validators=[validators.Length(min = 4, max = 34)])
    username = StringField("Username",validators=[validators.Length(min = 5, max = 15)])
    email = StringField("E-mail address",validators=[validators.Email()])
    password = PasswordField("Password",validators=[
        validators.DataRequired(),
        validators.EqualTo(fieldname="confirm")
    ])
    confirm = PasswordField("Confirm your password")

class LoginForm(Form):
    username = StringField("Username")
    password = PasswordField("Password")

app = Flask(__name__)
app.secret_key = "flaskblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "flaskblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    numbers = [1,2,3,4,5]
    return render_template("index.html",numbers = numbers)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():

        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        query = "Insert into users(name,username,email,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(query,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()

        flash("Successfully registered!","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        query = "Select * From users where username = %s"
        result = cursor.execute(query,(username,))
        
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Successfully logged in!","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Incorrect password!","danger")
                return redirect(url_for("login"))

        else:
            flash("Incorrect username!","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html", form=form)

@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "Select * From articles where id = %s"
    result = cursor.execute(query,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s"
    result = cursor.execute(query,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

@app.route("/addarticle",methods=["POST","GET"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Successfully added the article!","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form=form)

@app.route("/delete/<string:id>")
@login_required
def deletearticle(id):
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(query,(session["username"],id))

    if result > 0:
        query2 = "Delete From articles where id = %s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))

    else:
        flash("You cannot do this.","danger")
        return redirect(url_for("index"))


@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def updatearticle(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(query,(id,session["username"]))
        
        if result == 0:
            flash("There is no such article or you are not authorised to access it.","danger")
            return redirect(url_for("articles"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("updatearticle.html",form=form)

    else:
        form = ArticleForm(request.form)
        
        new_title = form.title.data
        new_content = form.content.data

        cursor = mysql.connection.cursor()
        query2 = "Update articles Set title = %s, content = %s where id = %s"
        cursor.execute(query2,(new_title,new_content,id))
        mysql.connection.commit()

        flash("Successfully editted the article!","succes")
        return redirect(url_for("dashboard"))


@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "Select * From articles"
    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "Select * From articles where title like '%" + keyword + "%' " 
        result = cursor.execute(query)

        if result == 0:
            flash("No matching article with the keyword!","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)


class ArticleForm(Form):
    title = StringField("Title")
    content = TextAreaField("Content")

if __name__ == "__main__":
    app.run(debug=True)

