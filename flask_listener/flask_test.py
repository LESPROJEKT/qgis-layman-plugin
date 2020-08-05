# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 16:17:30 2019

@author: Honza
"""

from flask import Flask, request, jsonify
import requests
import json
import tempfile
import os

app = Flask(__name__)

def writeCode(value):
    path = tempfile.gettempdir() + os.sep + "atlas" + os.sep + "auth.txt" 
    #path = r'C:\Users\Honza\AppData\Local\Temp\test.txt'
    f = open(path, "w")
    f.write(value)
    f.close()

@app.route('/')
def hello():
    return "Hello World!"


@app.route('/<name>')
def hello_name(name):
    return "Hello {}!".format(name)

@app.route("/client/authn/oauth2-liferay/callback", methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
def form_to_json():
    data = request.form.to_dict(flat=False)
    code = request.args.get('code')
    writeCode(code)
    #return (code)
    return "Authorize code optained. Please continue with QGIS plugin."

#@app.route("/client/authn/oauth2-liferay/code", methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
#def sendCode():   
#    API_ENDPOINT = "http://localhost:3000/client/authn/oauth2-liferay/callback"
#    return (authCode)    
#  #  return jsonify(c)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
