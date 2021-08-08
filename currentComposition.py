import requests
import re
import json
class CurrentComposition(object):
    def __init__(self, uri, name, workspace, header, user):       
        self.composition = list() 
        self.URI = uri
        self.name = name
        self.workspace = workspace
        self.header = header
        self.user = user
        


    def getComposition(self):
        return self.composition


    def getWorkspace(self):
        return self.workspace
    def getLayerNamesList(self):
        layerList = list()
        for layer in self.composition['layers']:
            layerList.append(layer['name'])
        return layerList
    def getVisibilityForLayer(self,layerName):
        for layer in self.composition['layers']:
            if self.removeUnacceptableChars(layerName) == self.removeUnacceptableChars(layer['title']):
                return layer['visibility']

    def getLayerList(self):
        layerList = list()
        for layer in self.composition['layers']:
            layerList.append(layer)
        return layerList
    

    def setComposition(self, json):
        self.composition = json

    def getComposition(self):
        return self.composition    

    def getPermissions(self): 
        url = self.URI+'/rest/'+self.workspace+'/maps/'+self.name+'/file'     
        r = requests.get(url = url, headers = self.header)
        data = r.json()
        try:
            self.user in data['access_rights']['write']
        except:
            return "n"
        if self.user in data['access_rights']['write'] or "EVERYONE" in data['access_rights']['write']:
            return "w"
        if self.user in data['access_rights']['read'] or "EVERYONE" in data['access_rights']['read']:
            return "r"     
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
        input = input.replace("ó","o")
        input = input.replace("č","c")
        input = input.replace("ď","d")
        input = input.replace("ě","e")
        input = input.replace("ť","t")
        input = input.replace("-","_")
        input = input.replace(".","_")
        input = input.replace(":","")
        input = input.replace("/","_")        
        input = input.replace("___","_")
        input = input.replace("__","_")
        input = re.sub(r'[?|$|.|!]',r'',input)
        try:
            if input[len(input) - 1] == "_":
                input = input[:-1]
        except:
            print("removechars exception")
       # iface.messageBar().pushWidget(iface.messageBar().createMessage("Layman:", "Diacritics in name of layer was replaced."), Qgis.Success, duration=3)
        #print("name after remove: " + input)
        return input        