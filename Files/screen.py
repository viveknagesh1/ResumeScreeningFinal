#status of dev branch
import glob
import os
from typing import List
import warnings
from random import uniform
from scipy.sparse.construct import random
import textract
import requests

from flask import (Flask, json, Blueprint, jsonify, redirect, render_template, request,
                   url_for)
from gensim.summarization import summarize
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from werkzeug.utils import secure_filename

# import pdf2txt as pdf
import PyPDF2
import ntpath
import re
import pdftotext
import io
#{name : vivek;must-to-have: "";}

warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')

class ResultElement:
    def __init__(self, rank, filename):
        self.rank = rank
        self.filename = filename


def getfilepath(loc):
    temp = str(loc)
    temp = temp.replace('\\', '/')
    return temp

def sanitise(detail):
    detail = detail.replace('\n', '')
    detail = detail.replace('\r', '')
    return detail

def getRanks(Resumes, mh, gh):
    corpus = []
    corpus.append(mh); corpus.append(gh)
    corpus.extend(Resumes)

    vector = TfidfVectorizer(min_df = 1, stop_words = "english")
    tfidf = vector.fit_transform(corpus) # vector of weights of words in all the N+1 docs
    doc_pair_similarity = tfidf * tfidf.T 
    # ^ matirx in which matrix[i][j] = similarity betw doc_i and doc_j 
    # ^ done using cosine similarity and tf-idf to find ditance betw. the docs (extent of similarity)
    doc_pair_similarity = doc_pair_similarity.toarray().tolist()
    resume_ranks = {'mh' : doc_pair_similarity[0][2:], 'gh' : doc_pair_similarity[1][2:]}
    num_resumes = len(resume_ranks['mh'])
    print('\n\nnum_resumes in getRanks : ', num_resumes, '\n')
    resume_ranks['mh'] = [[resume_ranks['mh'][i], i] for i in range(num_resumes)]
    resume_ranks['gh'] = [[resume_ranks['gh'][i], i] for i in range(num_resumes)]
    
    for ele in resume_ranks['mh']:
        if ele[0] == 0:
            ele[0] = uniform(1, 5)/100
        else:
            ele[0] += 0.10 * ele[0]
    for ele in resume_ranks['gh']:
        if ele[0] == 0:
            ele[0] = uniform(1, 5)/100
        else:
            ele[0] += 0.10 * ele[0]

    temp_list = sorted(zip(resume_ranks['mh'], resume_ranks['gh']), key = lambda x:x[0][0], reverse = True)
    print("\n\ntemp_list : ", temp_list, '\n\n')

    resume_ranks['mh'] = [x[0] for x in temp_list]
    resume_ranks['gh'] = [x[1] for x in temp_list]

    return resume_ranks

def extract_details(jd_content):
    # get must haves and good to haves from the jd file
    mh_patt = r"(?smi)^Must To Have((?!(\r?\n){2}).)*" or r"(?smi)^Must To Have Skills((?!(\r?\n){2}).)*"
    gh_patt = r"(?smi)^Good To Have((?!(\r?\n){2}).)*" or r"(?smi)^Good To Have Skills((?!(\r?\n){2}).)*"
    role_patt = r"(?smi)^Job Role((?!(\r?\n){2}).)*"
    years_exp_patt = r"(?smi)^Years of experience((?!(\r?\n){2}).)*"

    match_obj = re.search(mh_patt, jd_content)
    if not match_obj:
        return -1
    mh_text = match_obj.group()
    mh_text = mh_text[13:] # must haves

    match_obj = re.search(gh_patt, jd_content)
    if not match_obj:
        return -1
    gh_text = match_obj.group()
    gh_text = gh_text[13:] # good to haves

    match_obj = re.search(role_patt, jd_content)
    if not match_obj:
        return -1
    role_text = match_obj.group()
    role_text = role_text[9:] # Job Role

    match_obj = re.search(years_exp_patt, jd_content)
    if not match_obj:
        return -1
    years_exp_text = match_obj.group()
    years_exp_text = years_exp_text[20:] # Job Exp in Years

    mh_text = sanitise(mh_text) # remove \n\r\t so on
    gh_text = sanitise(gh_text)
    role_text = sanitise(role_text)
    years_exp_text = sanitise(years_exp_text)

    return (mh_text, gh_text, role_text, years_exp_text)

def readJD(jobfile):
    # jd_dir = os.path.dirname(jobfile)
    # os.chdir(jd_dir)
    # link_head, link_tail = ntpath.split(jobfile)
    # jd_name = link_tail or ntpath.basename(link_head)
    # jd_path = jd_dir + '/' + jd_name

    jd_name = jobfile.filename 
    jd_content = ''
    ext = jd_name.split('.')[1]
    jd_inp_file = 'jd_inp_content.' + ext.lower()

    jd_inp_content = jobfile.read()
    with open(jd_inp_file, 'wb') as f:
        f.write(jd_inp_content)

    if ext.lower() == 'pdf':
        try:
            jd_content = textract.process(jd_inp_file, method='pdfminer')
            jd_content = jd_content.decode('utf-8')
            # print('\n\nJD Content in readJD :\n', jd_inp_file, jd_path, ext, jd_content)
        except Exception as e: 
            print('\n\nProblem reading the JD PDF File\n\n')

    elif ext.lower() == 'doc' or ext.lower() == 'docx':
        try:
            jd_content = textract.process(jd_inp_file)
            jd_content = jd_content.decode('utf-8')
            jd_content = re.sub(r'\n{2}', '\n', jd_content)
            # print('\n\nJD Content in readJD doc(x) :\n', jd_inp_file, jd_path, ext, jd_content, '\n')
        except Exception as e: 
            print('\n\nProblem reading the JD doc/docx File\n\n')
    elif ext.lower() == 'txt':
        try:
            with open(jd_inp_file, 'r') as txt_file:
                jd_content = txt_file.read()
        except Exception as e: 
            print('\n\nProblem reading the JD txt File\n\n')
    else:
        print('\n\nUnsupported JD File Format\n\n')
        return -1
    
    return jd_content

def enhanceResRanks(resume_ranks, LIST_OF_FILES, mh_text, gh_text, role, years_exp):
    temp = {'all_resumes' : []}
    slno = 0
    for i in range(len(resume_ranks['mh'])):
        res_mh = resume_ranks['mh'][i]
        res_gh = resume_ranks['gh'][i]
        slno += 1
        res_filename = LIST_OF_FILES[res_mh[1]]
        res_rank_mh = str(round((res_mh[0] * 100), 2)) + '%'
        res_rank_gh = str(round((res_gh[0] * 100), 2)) + '%'
        temp_dict = {'slno' : slno, 'filename' : res_filename, 'rank_mh' : res_rank_mh, 'rank_gh' : res_rank_gh}
        temp['all_resumes'].append(temp_dict)
    
    temp['mh_text'] = mh_text
    temp['gh_text'] = gh_text
    temp['role'] = role
    temp['years_exp'] = years_exp
    
    return temp

def readAllResumes(all_res_files, LIST_OF_FILES, LIST_OF_FILES_PDF, LIST_OF_FILES_DOC, LIST_OF_FILES_DOCX, Resumes):
    #Resume FILES

    Temp_pdf = ''
    # os.chdir(res_dir_path)
    #os.chdir() method used to change the current working directory to specified path.

    ## glob module is used to retrieve files/pathnames matching a specified pattern.
    # for file in glob.glob('**/*.pdf', recursive=True):
    #     LIST_OF_FILES_PDF.append(file)
    # for file in glob.glob('**/*.doc', recursive=True):
    #     LIST_OF_FILES_DOC.append(file)
    # for file in glob.glob('**/*.docx', recursive=True):
    #     LIST_OF_FILES_DOCX.append(file)

    # LIST_OF_FILES.extend(LIST_OF_FILES_DOC + LIST_OF_FILES_DOCX + LIST_OF_FILES_PDF)
    # LIST_OF_FILES = deepcopy(all_res_files)
    
    LIST_OF_FILES.extend([file.filename for file in all_res_files])
    
    for nooo,i in enumerate(all_res_files):  #Enumerate() method adds a counter to an iterable and returns it in the form of an enumerate object.
        # Ordered_list_Resume.append(i)
        Temp = i.filename.split(".")

        temp_res_file = 'temp_res_file.' + Temp[1]

        try:
            with open(temp_res_file, 'wb') as op_file:
                    op_file.write(i.read())

            if Temp[1].lower() == "pdf":
                try:
                    with open(temp_res_file,'rb') as pdf_file:
                        read_pdf = PyPDF2.PdfFileReader(pdf_file)
                        number_of_pages = read_pdf.getNumPages()
                        for page_number in range(number_of_pages): 

                            page = read_pdf.getPage(page_number)
                            page_content = page.extractText()
                            page_content = page_content.replace('\n', ' ')
                            Temp_pdf = str(Temp_pdf) + str(page_content)
                        Resumes.extend([Temp_pdf])
                        Temp_pdf = ''

                except Exception as e: print(e)
            elif Temp[1].lower() == "doc":
                try:
                    a = textract.process(temp_res_file)
                    a = a.replace(b'\n',  b' ')
                    a = a.replace(b'\r',  b' ')
                    b = str(a)
                    c = [b]
                    Resumes.extend(c)
                except Exception as e: print(e)
                    
                    
            elif Temp[1].lower() == "docx":
                try:
                    a = textract.process(temp_res_file)
                    a = a.replace(b'\n',  b' ')
                    a = a.replace(b'\r',  b' ')
                    b = str(a)
                    c = [b]
                    Resumes.extend(c)
                except Exception as e: print(e)
                        
                    
            else:
                print("\nUNSUPPORTED FILE FORMAT")
                pass
        except Exception as e: 
            print("\nUnexpected exception while readinf resume file : ", e)


def result_manually(manual_jd_dict):
    LIST_OF_FILES = []
    LIST_OF_FILES_PDF = []
    LIST_OF_FILES_DOC = []
    LIST_OF_FILES_DOCX = []
    Resumes = []
    
    all_res1 = manual_jd_dict['all_res']
    readAllResumes(all_res1, LIST_OF_FILES, LIST_OF_FILES_PDF, LIST_OF_FILES_DOC, LIST_OF_FILES_DOCX, Resumes)

    role_text = "Role: " + manual_jd_dict['role'] + '\n'
    years_exp_text = "Years of Experience: " + manual_jd_dict['yoe'] + '\n'
    mh_text = "Must to have skills: " + manual_jd_dict['mh_skills'] + '\n'
    gh_text = "Good to have skills: " + manual_jd_dict['gh_skills'] + '\n'

    # rank resumes on the manually entered JD details and return them
    resume_ranks = getRanks(Resumes, role_text + mh_text + years_exp_text, role_text + gh_text + years_exp_text)
    print('\n\nResume Ranks in result_manually : ', resume_ranks, '\n')
    resume_ranks = enhanceResRanks(resume_ranks, LIST_OF_FILES, mh_text, gh_text, role_text, years_exp_text)
    return resume_ranks

def res(jobfile, all_res_files):

    print("\n\nCAME CAME CAME")

    LIST_OF_FILES = []
    LIST_OF_FILES_PDF = []
    LIST_OF_FILES_DOC = []
    LIST_OF_FILES_DOCX = []
    Resumes = []

    readAllResumes(all_res_files, LIST_OF_FILES, LIST_OF_FILES_PDF, LIST_OF_FILES_DOC, LIST_OF_FILES_DOCX, Resumes)

    print("Done Parsing.")

    jd_content = readJD(jobfile)
    if jd_content == -1:
        # err
        return []

    # Resumes : list of all original resumes text contents
    # jd_content : given JD's text content

    # extract must haves and good to haves
    details = extract_details(jd_content)
    if details == -1:
        # err
        return []
    
    mh_text, gh_text, role_text, years_exp_text = details[0], details[1], details[2], details[3]
    
    mh_text = "Must to have skills: " + mh_text + '\n'
    gh_text = "Good to have skills: " + gh_text + '\n'
    role_text = "Role: " + role_text + '\n'
    years_exp_text = "Years of experience: " + years_exp_text + '\n'

    print('\n\nnum_resumes : ', len(Resumes), len(LIST_OF_FILES), '\n')

    print("\n\nmh & gh : \n", mh_text, gh_text, '\n\n', sep = '\n\n')
    resume_ranks = getRanks(Resumes, role_text + mh_text + years_exp_text, role_text + gh_text + years_exp_text)

    print("\n\nHighest JD match to lowest (mh & gh in order) : \n\n")
    for ele in resume_ranks['mh']:
        print('Resume_' + str(ele[1] + 1) + ' :', ele[0])
    print()
    for ele in resume_ranks['gh']:
        print('Resume_' + str(ele[1] + 1) + ' :', ele[0])
    
    print('\n')
    resume_ranks = enhanceResRanks(resume_ranks, LIST_OF_FILES, mh_text, gh_text, role_text, years_exp_text)
    return resume_ranks


if __name__ == '__main__':
    inputStr = input("")
    # sear(inputStr)

'''

# after done parsing

Job_Desc = 0
    LIST_OF_TXT_FILES = []
    os.chdir('/Users/shashankvijay9980/Desktop/ResumeScanner/Files/Job_Description')
    # f = open(jobfile , 'r',encoding='cp1252',errors="ignore")
    f = open(jobfile , 'r',encoding='cp1252')
    text = f.read()
        
    try:
        tttt = str(text)
        tttt = summarize(tttt, word_count=100)
        text = [tttt]
    except:
        text = 'None'

    f.close()

    vectorizer = TfidfVectorizer(stop_words='english')
    # print(text)
    vectorizer.fit(text)
    vector = vectorizer.transform(text)

    Job_Desc = vector.toarray()
    # print("\n\n")
    # print("This is job desc : " , Job_Desc)

    os.chdir('../')
    for i in Resumes:

        text = i
        tttt = str(text)
        try:
            tttt = summarize(tttt, word_count=100) 
            text = [tttt]
            vector = vectorizer.transform(text)
            #SKLEARN function - Convert a collection of text documents to a matrix of token counts
            #Transform documents to document-term matrix.Extract token counts out of raw text documents using the vocabulary fitted with fit or the one provided to the constructor.
            aaa = vector.toarray()
            Resume_Vector.append(vector.toarray())
        except:
            pass
    # print(Resume_Vector)

    #Using KNN
    for i in Resume_Vector:

        samples = i
        neigh = NearestNeighbors(n_neighbors=1)
        neigh.fit(samples) 
        NearestNeighbors(algorithm='auto', leaf_size=30)

        Ordered_list_Resume_Score.extend(neigh.kneighbors(Job_Desc)[0][0].tolist())

    Z = [x for _,x in sorted(zip(Ordered_list_Resume_Score,Ordered_list_Resume))]
    print(Ordered_list_Resume)
    print(Ordered_list_Resume_Score)
    flask_return = []
    # for n,i in enumerate(Z):
    #     print("Rankkkkk\t" , n+1, ":\t" , i)

    for n,i in enumerate(Z):
        # print("Rank\t" , n+1, ":\t" , i)
        # flask_return.append(str("Rank\t" , n+1, ":\t" , i))
        name = getfilepath(i)
        #name = name.split('.')[0]
        rank = n+1
        res = ResultElement(rank, name)
        flask_return.append(res)
        # res.printresult()
        print(f"Rank{res.rank+1} :\t {res.filename}")
    return flask_return

'''