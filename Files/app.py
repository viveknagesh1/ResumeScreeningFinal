##COmmiting on git
import glob
import os
import warnings
from flask import make_response
import textract
import requests
import pymongo
from flask_pymongo import PyMongo
import bcrypt
import re
from datetime import timedelta
from flask_socketio import SocketIO, emit
# from flask.ext.login import current_user, logout_user

import redis
from flask import (Flask,session, g, json, Blueprint,flash, jsonify, redirect, render_template, request,url_for, send_from_directory)

from gensim.summarization import summarize
#Gensim is a Python library for topic modelling, document indexing and similarity retrieval with large corpora. Target audience is the natural language processing (NLP) and information retrieval (IR) community.

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


from werkzeug.utils import secure_filename  
import screen
import hashlib

from flask import Flask, render_template, redirect, request, session
from flask_session import Session

#It is a WSGI toolkit, which implements requests, response objects, and other utility functions. This enables building a web framework on top of it. The Flask framework uses Werkzeug as one of its bases.


# import pdf2txt as pdf
import PyPDF2

warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')

app = Flask(__name__)


app.config.from_object(__name__) # load config from this file , flaskr.py




# Load default config and override config from an environment variable
app.config.update(dict(
    USERNAME='admin',
    PASSWORD='7b4d7a208a333b46acdc9da159e5be7a',
    SECRET_KEY='development key',
))
socketio = SocketIO(app)
@socketio.on('disconnect')
def disconnect_user():
    #logout_user()
    session["logged_in"]=False
    session.pop('development key', None)

# app.config['SESSION_TYPE'] = 'redis'
# app.config['SESSION_PERMANENT'] = False
# app.config['SESSION_USE_SIGNER'] = True
# app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:27017')

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["MONGO_URI"] = "mongodb+srv://viveknagesh1:Vivek0935@ltts.jjzpl.mongodb.net/ltts?retryWrites=true&w=majority"
#app.config["MONGO_URI"] = "mongodb://localhost:27017/ltts"

mongo = PyMongo(app)
db = mongo.db

#app.config['UPLOAD_FOLDER'] = 'Original_Resumes/'
app.config['UPLOAD_FOLDER'] = '/'

app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

class jd:
    def __init__(self, name):
        self.name = name

def getfilepath(loc):
    temp = str(loc).split('\\')
    return temp[-1]
    



@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    else:
        error = None
        res=None
        global mongo
        if request.method == 'POST':
            users=mongo.db.users
            login_user=users.find_one({'username':request.form['username']})
            # print(bcrypt.hashpw(request.form['password'].encode('cp1252'),bcrypt.gensalt()))
            if login_user:
                if bcrypt.hashpw(request.form['password'].encode('cp1252'),login_user['password']) == login_user['password']:
                    # print("\n\nPwds mathc\n\n")
                    session['username'] = request.form['username']
                    session['logged_in'] = True
                    return redirect(url_for('selectpdf'))
                else:
                    # print("passwords do not match")
                    res="passwords do not match"
                    return "<script>alert('Wrong username/password. Please try again!'); location.reload(); </script>"
            else:
                return "<script>alert('Wrong username/password. Please try again!'); location.reload(); </script>"  

        return render_template('signin_final.html', error=error,res=res)




@app.route('/signup',methods=['GET', 'POST'])
def signup():
     if session.get('logged_in'):
        return redirect(url_for('home'))
     else:
        if request.method=='POST':
            users=mongo.db.users
            # users.insert({'name':request.form['username'],'password':request.form['password']})
            #return redirect(url_for('home'))
            existing_user=users.find_one({'name':request.form['username']})
            if existing_user is None:
                hashpass=bcrypt.hashpw(request.form['password'].encode('cp1252'),bcrypt.gensalt())
                #elif app.config['PASSWORD'] != hashlib.md5(request.form['password'].encode('cp1252')).hexdigest():

                users.insert({'username':request.form['username'],'password':hashpass,'email':request.form['email'],'name':request.form['name'],'new_jd_dict':[]}) 
                session['username']=request.form['username']  
                session['logged_in'] = True

                return redirect(url_for('selectpdf')) 
            return 'Username already exists'
                
        return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username',None)
    flash('You were logged out')
    return redirect(url_for('home'))

@app.route('/selectpdf')
def selectpdf():
    if session.get('logged_in'):
        # current working dir
        cwd = os.path.abspath(os.getcwd())
        if("/Job_Description" not in cwd):
            jd_dir = cwd + '/Job_Description/*'
        else:
            jd_dir = cwd + '/*'
        selectuser=""
        x = []
        # print("\n\njd_dir in selectpdf : ", jd_dir, '\n')
        # "/Users/shashankvijay9980/Desktop/ResumeScanner/Files/Job_Description/*"
        for file in glob.glob(jd_dir):
            # print("\n\n cwd is ",cwd,"\n\n")
            # /Users/viveknagesh1/No_cloud/LTTS_Sprint_3/Files/Job_Description
            res = jd(file)
            x.append(jd(getfilepath(file)))
        # print("\n\nJD Objs. : ", x,'\n')  
        users=mongo.db.users
        user_data=list(users.find())
        # print('\n\nuser_data : ', user_data, '\n\n')

    
        y=[]
        username=session['username']
        userDetails=users.find_one({'username':username})['new_jd_dict']
        for r in userDetails:
            y.append(r)

            # y.insert(0,r)
        y=y[::-1]
        return render_template('selectpdf.html',results = x,directories=y)
    else:
        return redirect(url_for('home'))

@app.route('/')
def home():
    # x = []
    # for file in glob.glob("/Users/viveknagesh1/Downloads/Automated-Resume-Screening-System-master/Job_Description/*.txt"):
    #     res = jd(file)
    #     x.append(jd(getfilepath(file)))
    # print(x)
    
    return render_template('index.html')

@app.route('/search_string', methods = ['POST'])
def search_string():
    # inp = request.get_json()
    # inp = json.loads(request.form['data'])
    # print('\n\ninp : ', inp, type(inp), '\n')
    # search_str = inp['searchstring']
    # selected_res = inp['resFileMultiple']

    # print('\nrequest.files : ', request.files.getlist('resFileMultiple'))
    
    selected_res = request.files.getlist('resFileMultiple')
    search_str = request.form['searchstring']

    print('\n', selected_res, '\n', search_str)

    LIST_OF_FILES = []; Resumes = []
    screen.readAllResumes(selected_res, LIST_OF_FILES, [], [], [], Resumes)

    res_with_searchstr_list = []

    num_res = len(Resumes)
    for i in range(num_res):
        res_content = Resumes[i]
        match = 0
        match = re.search(re.escape(search_str), re.escape(res_content), re.IGNORECASE)

        if match:
            # match found
            res_with_searchstr = LIST_OF_FILES[i]
            res_with_searchstr_list.append(res_with_searchstr)

    # print('\n\nres_with_searchstr_list : ', res_with_searchstr_list, '\n')

    return json.dumps(res_with_searchstr_list)

@app.route('/results_manually', methods = ['GET', 'POST'])
def res_maually():
    manual_jd_dict = {}
    manual_jd_dict['role'] = request.form['role']
    manual_jd_dict['yoe'] = request.form['yoe']
    manual_jd_dict['mh_skills'] = request.form['mh_skills']
    manual_jd_dict['gh_skills'] = request.form['gh_skills']
    manual_jd_dict['all_res'] = request.files.getlist('resFileMultiple')

    print('\n\n', manual_jd_dict, ': \n', request.files.getlist('all_res'), '\n')

    flask_return = screen.result_manually(manual_jd_dict)
    return render_template('result.html', results = flask_return)
    # return "1"

@app.route('/results', methods=['GET', 'POST'])
def res():
    if session.get('logged_in'):
        if request.method == 'POST':
            
            print("\n\nin post CAME : ", request.files['jd_file'].filename)

            all_res_files = request.files.getlist('resFileMultiple')
            
            # new_jd_dict=request.form['new_jd_dict']
            # if(new_jd_dict==''):
            #     new_jd_dict=request.form['directory']
            
            users=mongo.db.users
            username=session['username']

            userDetails=users.find_one({'username':username})['new_jd_dict']
            
            # if(new_jd_dict==''):
            #     print("EMPTY SO DONT STORE IN DATABASE")
            # elif(new_jd_dict in userDetails):
            #     print("\n\nThis directory already exists :", new_jd_dict, '\n\n')
            # else:
            #     dbUpdate=users.update_one(
            #     {"username":session['username']},
            #     {"$push":{"new_jd_dict":new_jd_dict}}
            #     )
            
            # jobfile = request.form['des']
            jobfile = request.files['jd_file']
            
            flask_return = screen.res(jobfile, all_res_files)

            if flask_return==-1 or flask_return==[]:
                return "<script>alert('Please Enter the JD Manually'); location.reload(); </script>"
            return render_template('result.html', results = flask_return)
        else:
            return redirect(url_for('home'))

@app.route('/resultscreen' ,  methods = ['POST', 'GET'])
def resultscreen():
    if request.method == 'POST':

        jobfile = request.form.get('Name')
        # print(jobfile)
        flask_return = screen.res(jobfile)
        return render_template('result.html', results = flask_return)



# @app.route('/resultsearch' ,methods = ['POST', 'GET'])
# def resultsearch():
#     if request.method == 'POST':
#         # search_st = request.form.get('Name')
#         # print(search_st)
#         # result = search.res(search_st)
#         # jd_dict=mongo.db.jd_dict
#         # new_jd_dict=jd_dict.find_one('new_jd_dict':request.form['new_jd_dict']})
#         # if new_jd_dict:
#         #     print("Directory is already existing")
#         users=mongo.db.users
#         login_user=users.find_one({'username':session['username']})
#         new_jd_dict=request.form['new_jd_dict']
#         myquery={'username':session['username']}
#         newvalues={"$set":{'new_jd_dict':new_jd_dict}}
#         login_user=
#         if(new_jd_dict in login_user):
#             print("This directory already exists")
#         else:
#             users.update_one(myquery,newvalues)
#         # print(bcrypt.hashpw(request.form['password'].encode('cp1252'),bcrypt.gensalt()))
#         #     if login_user:
#         #         if bcrypt.hashpw(request.form['password'].encode('cp1252'),login_user['password']) == login_user['password']:
#         #             session['username'] = request.form['username']
#         #             session['logged_in'] = True
#         #             return redirect(url_for('selectpdf'))
#         #         else:
#         #             print("passwords do not match")
#         #             res="passwords do not match"



#     # return result
#     # return render_template('result.html', results = result)
#     return render_template('result.html')


@app.route('/Original_Resume/<path:filename>')
def custom_static(filename):
    return send_from_directory('./Original_Resumes', filename)



if __name__ == '__main__':
   # app.run(debug = True) 
    # app.run('127.0.0.1' , 5000 , debug=True)
    app.run('0.0.0.0' , 5002 , debug=True , threaded=True)
    
    
