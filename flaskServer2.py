# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 16:17:30 2019

@author: Honza
"""

from flask import Flask, request, jsonify
import threading
class flaskServer(object):
                                                                   
       

     data = 'foo'
     print (data)
     app = Flask(__name__)
     app.run(host='0.0.0.0', port=3000)
    # threading.Thread(target=app.run).start()
     @app.route("/")
     def main():
         print(data)
         return "Layman"
#     @app.route("/client/authn/oauth2-liferay/callback", methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
#     def form_to_json(self):
#         data = request.form.to_dict(flat=False)
#         code = request.args.get('code')   
#      
#         return (code)
#     def startServer():
#         print("test")
#         app.run(host='0.0.0.0', port=3000)

     #if __name__ == "__main__":
     #    print("flask is starting")
     #    threading.Thread(target=app.run).start()
    #app = Flask(__name__)
    #app.run(host='0.0.0.0', port=3000)
    ##def __init__(self):
    ##    app = Flask(__name__)
    ##    #if __name__ == '__main__':
    ##    app.run(host='0.0.0.0', port=3000)

    #@app.route('/')
    #def hello():
    #    return "Hello World!"


    #@app.route('/<name>')
    #def hello_name(name):
    #    return "Hello {}!".format(name)

    #@app.route("/client/authn/oauth2-liferay/callback", methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
    ##def get_text():
    ##    return "some text"
    ##def add():                                                                                                                              
    ##    data = request.get_json()
    #    # ... do your business logic, and return some response
    #    # e.g. below we're just echo-ing back the received JSON data
    #  # print (jsonify(data))
    #   # print (request.headers)
    #   # print (request.__dict__)
    #    print (request.data)
    #    return jsonify(data)
    #def form_to_json(self):
    #    data = request.form.to_dict(flat=False)
    #    code = request.args.get('code')
    
    #    return jsonify(data)
    #    return (code)


    