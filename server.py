from handle.email import Register
from flask import flash,url_for,render_template,Flask,session,request
app = Flask(__name__)
app.secret_key = "secret"
@app.route('/')
def home():
    return render_template("login.html")
@app.route('register',methods=["POST",'GET'])
def register():
    pass