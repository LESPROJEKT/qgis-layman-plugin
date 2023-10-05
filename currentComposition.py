import requests
import re
from qgis.core import *

class CurrentComposition(object):
    def __init__(self, uri, name, workspace, header, user):       
        self.composition = list() 
        self.URI = uri
        self.name = name
        self.workspace = workspace
        self.header = header
        self.user = user
        self.layerIds = list()
        self.layers = list()


    def getComposition(self):
        return self.composition


    def getWorkspace(self):
        return self.workspace
    def getLayerNamesList(self):
        layerList = list()
        for layer in self.composition['layers']:
            layerList.append(self.removeUnacceptableChars(layer['title']))
        return layerList
    def isLayerInComposition(self, layerName):
        pom = False
        for layer in self.composition['layers']:
            if self.removeUnacceptableChars(layer['title']) == layerName:
                pom = True
        return pom
    def getVisibilityForLayer(self,layerName):
        for layer in self.composition['layers']:
            if self.removeUnacceptableChars(layerName) == self.removeUnacceptableChars(layer['title']):
                return layer['visibility']
    def getServiceForLayer(self,layerName):
        for layer in self.composition['layers']:          
            if self.removeUnacceptableChars(layerName) == self.removeUnacceptableChars(layer['title']):
                print(layerName , layer['className'])
                print(layer['className'] == "HSLayers.Layer.WMS")
                return layer['className']
            
            
    def isLayerId(self, id):
        if id in self.layerIds:
            return True
        else:
            return False
    def changeLayerId(self, layer):
        for i in range(0, len(self.layers)):
            if self.layers[i].name() == layer.name():
                self.layerIds[i] = layer.id()
     
    def getLayerList(self):
        layerList = list()
        for layer in self.composition['layers']:
            layerList.append(layer)
        return layerList
    def getUrl(self):
        if "client" in self.URI:
            return self.URI+'/rest/'+self.workspace+'/maps/'+self.name+'/file'
        else:
            return self.URI+'/client/rest/'+self.workspace+'/maps/'+self.name+'/file'
    def setIds(self, layers):
        for layer in layers:
            self.layerIds.append(layer.id())
            self.layers.append(layer)
    def setComposition(self, json):
        self.composition = json

    def getComposition(self):
        return self.composition    
    def refreshComposition(self):      
        url = self.URI+'/rest/'+self.workspace+'/maps/'+self.name+'/file'     
        r = requests.get(url = url, headers = self.header)
        data = r.json()
        self.composition = data
    def getPermissions(self): 
        url = self.URI+'/rest/'+self.workspace+'/maps/'+self.name+'/file'     
        r = requests.get(url = url, headers = self.header)
        data = r.json()
        if 'access_rights' in data and 'write' in data['access_rights']:
            if self.user in data['access_rights']['write'] or "EVERYONE" in data['access_rights']['write']:
                print("w")
                return "w"
        if 'access_rights' in data and 'read' in data['access_rights']:
            if self.user in data['access_rights']['read'] or "EVERYONE" in data['access_rights']['read']:
                print("r")
                return "r"
        print("n")
        return "n"
    def hasLaymanLayer(self):
        for layer in self.composition['layers']:
            if layer['className'] == "OpenLayers.Layer.Vector":
                if '/geoserver/' in layer['protocol']['url']:
                    return True
            if layer['className'] == "HSLayers.Layer.WMS":
                if '/geoserver/' in layer['url']:
                    return True
        return False
    def getLayerOrderByTitle(self, title):
        for i in range (0,len(self.composition['layers'])):
            if self.composition['layers'][i]['title'] == title: 
                return i
    def getAllPermissions(self):
        url = self.URI+'/rest/'+self.workspace+'/maps/'+self.name     
        r = requests.get(url = url, headers = self.header)
        data = r.json()
        print(data)
        return data['access_rights']
    def removeUnacceptableChars(self, input):
        input = input.lower()
        input = input.replace("ř","r")
        input = input.replace("š","s")
        input = input.replace("ž","z")
        input = input.replace("ů","u")
        input = input.replace("ú","u")
        input = input.replace(" ","_")
        input = input.replace("é","e")
        input = input.replace("í","i")
        input = input.replace("ý","y")
        input = input.replace("á","a")
        input = input.replace("ň","n")
        input = input.replace("ó","o")
        input = input.replace("č","c")
        input = input.replace("ď","d")
        input = input.replace("ě","e")
        input = input.replace("ť","t")
        input = input.replace("-","_")
        input = input.replace(".","_")
        input = input.replace(":","")
        input = input.replace("/","_")
        input = input.replace("(","")
        input = input.replace(")","")
        input = input.replace("___","_")
        input = input.replace("__","_")
        input = re.sub(r'[?|$|.|!]',r'',input)
        input = re.sub(r'[?|$|.|!]',r'',input)
        try:
            if input[len(input) - 1] == "_":
                input = input[:-1]
        except:
            print("removechars exception")
       
        return input        