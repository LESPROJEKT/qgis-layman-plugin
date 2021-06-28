import requests
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