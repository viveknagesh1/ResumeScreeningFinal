

import glob
import os
import warnings
import textract
import bcrypt
import requests
from flask_pymongo import PyMongo

from flask import (Flask,session, g, json, Blueprint,flash, jsonify, redirect, render_template, request,url_for, send_from_directory)
from werkzeug.utils import secure_filename   

#It is a WSGI toolkit, which implements requests, response objects, and other utility functions. This enables building a web framework on top of it. The Flask framework uses Werkzeug as one of its bases.
    
import hashlib

PEOPLE_FOLDER = os.path.join('static', 'people_photo')


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = PEOPLE_FOLDER

app.config.from_object(__name__) # load config from this file , flaskr.py

app.config["MONGO_URI"] = "mongodb://localhost:27017/ltts"
mongo = PyMongo(app)
db = mongo.db



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return 'You are logged in as '+session['username']
    return render_template('signin.html')

@app.route('/logout')
def logout():
    return redirect(url_for('home'))


@app.route('/')
def home():
    full_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'shovon.jpg')
    return render_template('index.html', user_image = full_filename)

@app.route('/signup',methods=['GET', 'POST'])
def signup():
    if request.method=='POST':
        users=mongo.db.users
        existing_user=users.find_one({'name':request.form['username']})
        if existing_user is None:
            hashpass=bcrypt.hashpw(request.fomr['pass'],bcrypt.genSalt())
            users.insert({'name':request.form['username'],'password':hashpass}) 
            session['username']=request.form['username']  
            return redirect(url_for('home')) 
        return 'Username already exists'    
    return render_template('signup.html')



if __name__ == '__main__':
    app.run('0.0.0.0' , 5001 , debug=True , threaded=True)
    
