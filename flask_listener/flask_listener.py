# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 16:17:30 2019

@author: Honza
"""

from flask import Flask, request, jsonify
import json
import tempfile
import os

app = Flask(__name__)

def writeCode(value):
    path = tempfile.gettempdir() + os.sep + "atlas" + os.sep + "auth.txt"    
    f = open(path, "w")
    f.write(value)
    f.close()

@app.route('/')
def hello():
    return "Flask server"


@app.route("/client/authn/oauth2-liferay/callback", methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
def form_to_json():
    data = request.form.to_dict(flat=False)
    code = request.args.get('code')
    writeCode(code)
    return "Authorization code obtained. You can now switch back to QGIS and continue."



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3857)
