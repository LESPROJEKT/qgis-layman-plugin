import json
import requests
import configparser
import os
import re
import PyQt5
from qgis.core import *
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QByteArray, Qt
import io
from PyQt5.QtNetwork import  QNetworkRequest
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox, QApplication
from qgis.PyQt.QtGui import QGuiApplication
from .dlg_errMsg import ErrMsgDialog
import tempfile
from PyQt5 import QtWidgets, QtGui, QtCore
import csv
import http.client
import asyncio
import ssl
import urllib.parse

class LaymanUtils(QObject): 
    showErr = pyqtSignal(list,str,str,Qgis.MessageLevel, str)  
    setVisibility = pyqtSignal(QgsMapLayer)
    loadStyle = pyqtSignal(QgsMapLayer)
    emitMessageBox = pyqtSignal(list)
    showQBar = pyqtSignal(list,Qgis.MessageLevel)
      
    def __init__(self, iface, locale,laymanUsername,  parent=None):
        super(LaymanUtils, self).__init__(parent=parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.isAuthorized = False
        self.URI = ""
        self.locale = locale
        self.iface = iface
        self.laymanUsername = laymanUsername
        self.currentLayer = []
        self.connectEvents()
    def connectEvents(self):         
        self.showErr.connect(self.showMessageError)
        self.setVisibility.connect(self._setVisibility)
        self.loadStyle.connect(self._loadStyle)
        self.emitMessageBox.connect(self._onEmitMessageBox) 
        self.showQBar.connect(self.showQgisBar)
    def getConfigItem(self, key):
        file =  os.getenv("HOME") + os.sep + ".layman" + os.sep + 'layman_user.INI'
        config = configparser.RawConfigParser()
        config.read(file)
        try:
            return config.get('DEFAULT', key)
        except configparser.NoOptionError:
            return None   
        
    def getDPI(self):
        return self.iface.mainWindow().physicalDpiX()/self.iface.mainWindow().logicalDpiX()      
               
    def requestWrapper(self, type, url, payload = None, files = None, emitErr = True):       
        try:
            response = requests.request(type, url = url, headers=self.getAuthHeader(self.authCfg), data=payload, files=files) 
        except Exception as ex:   
            info = str(ex)            
            self.showErr.emit(["Připojení není k dispozici","Connection is not available"],info, str(info), Qgis.Warning, "")                
            return       
        if emitErr:
            if response.status_code != 200: 
                print(url)              
                self.showErr.emit(["Požadavek nebyl úspěšný", "Request was not successfull"], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)    
        return response        
    async def asyncRequestWrapper(self, type, url, payload=None, files=None, emitErr=True):
        parsed_url = urllib.parse.urlparse(url)  
        host = parsed_url.netloc
        port = 443
        path = parsed_url.path + '?' + parsed_url.query     
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE              
        if type == "GET":
            conn = http.client.HTTPSConnection(host, port, context=context)
            conn.request("GET", path, headers=self.getAuthHeader(self.authCfg))
        elif type == "POST":
            conn = http.client.HTTPSConnection(host, port, context=context)
            conn.request("POST", path, body=payload, headers=self.getAuthHeader(self.authCfg))
      
            
        response = await asyncio.to_thread(conn.getresponse)
        response_content = response.read()
        if emitErr and response.status != 200:
            # Zpracování chybového stavu a emitování chybové zprávy
            content = response_content.decode('utf-8')
            self.showErr.emit(["Požadavek nebyl úspěšný", "Request was not successful"], f"code: {response.status}", content, Qgis.Warning, url)
        conn.close()  
        return response_content
       
  
    def recalculateDPI(self):
        self.DPI = self.getDPI()
        if self.DPI < 0.85:
            self.fontSize = "12px"
        else:
            self.fontSize = "10px"  
            
    def tranformCoords(self, xmin, xmax, ymin, ymax, src, dest = 4326):        
        dest = QgsCoordinateReferenceSystem(dest)
        tform = QgsCoordinateTransform(src, dest, QgsProject.instance())
        max = tform.transform(QgsPointXY(float(xmax),float(ymax)))
        min = tform.transform(QgsPointXY(float(xmin),float(ymin)))        
        return [min.x(), max.x(), min.y(), max.y()]      
             
    def showMessageError(self, text, info, err, typ, url):     
        widget = QWidget()
        layout = QHBoxLayout() 
        layout.setAlignment(Qt.AlignCenter)       
        #layout.addWidget(QLabel("Layman - "+ text[0] if self.locale == "cs" else text[1]))
        button = QPushButton("Více informací" if self.locale == "cs" else "More info")
        label2 = self.iface.messageBar().createMessage("Layman:", text[0] if self.locale == "cs" else text[1])
        layout.addWidget(label2)
        layout.addWidget(button)
        widget.setLayout(layout)
       
        def showDlg():
            self.dlgErr = ErrMsgDialog()            
            self.dlgErr.setWindowFlags(self.dlgErr.windowFlags() | Qt.WindowStaysOnTopHint)
            self.dlgErr.pushButton_copyMsg.setStyleSheet("color: #fff !important; text-transform: uppercase;font-size:"+self.fontSize+";  text-decoration: none;   background: #72c02c;   padding: 6px;  border-radius: 50px;    display: inline-block; border: none;transition: all 0.4s ease 0s;") # Add the stylesheet             
            self.dlgErr.pushButton_copyMsg.clicked.connect(copy_to_clipboard)
            self.dlgErr.plainTextEdit.setPlainText(text[0] +" - "+ str(info) if self.locale == "cs" else text[1] +" - " + str(info))
            self.dlgErr.show()

        def copy_to_clipboard():
            message = str(err) if url == "" else str(err) + "\n" + "requested url: " + url
            clipboard = PyQt5.QtGui.QGuiApplication.clipboard()
            clipboard.setText(message)
            self.dlgErr.close()        
        button.clicked.connect(showDlg)        
        self.iface.messageBar().pushWidget(widget, typ)    
    def setPortValue(self, index):
        if index == 0:
            self.saveToIni("port", "7070") 
            self.port = "7070"
        elif index == 1:
            self.saveToIni("port", "7071")  
            self.port = "7071" 
        elif index == 2:
            self.saveToIni("port", "7072") 
            self.port = "7072"  
        if index in (0,1,2) and self.port:            
            self.showQgisBar(["Port byl uložen.","Port has been saved."], Qgis.Success)      
                
    def saveToIni(self, key, value):
        self.appendIniItem(key, value)  
          
    def appendIniItem(self, key, item):
        file =  os.getenv("HOME") + os.sep + ".layman" + os.sep + 'layman_user.INI'
        config = configparser.RawConfigParser()
        config.read(file)
        config.set('DEFAULT',key,item)
        cfgfile = open(file,'w')
        config.write(cfgfile, space_around_delimiters=False)  # use flag in case case you need to avoid white space.
        cfgfile.close()                       
    def getVersion(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(self.plugin_dir ,'metadata.txt'))
        version = config.get('general', 'version')
        return(version)        
    def checkVersion(self):        
        r = requests.get("https://raw.githubusercontent.com/LESPROJEKT/qgis-layman-plugin/master/metadata.txt")
        buf = io.StringIO(r.text)
        config = configparser.ConfigParser()
        config.read_file(buf)
        version = config.get('general', 'version')
        installedVersion = self.getVersion()
        if installedVersion == version:
            return [True, version]
        else:
            return [False, version]
    def setAuthCfg(self,authCfg):
        self.authCfg = authCfg        
    def getAuthHeader(self, authCfg): 
        if self.isAuthorized:
            config = QgsAuthMethodConfig()            
            url = QUrl(self.URI+ "/rest/current-user")
            req = QNetworkRequest(url)   
            i = 0
            success = QgsApplication.authManager().updateNetworkRequest(req, authCfg)                 
            if success[0] == True:
                header = (req.rawHeader(QByteArray(b"Authorization")))  
                authHeader ={
                  "Authorization": str(header, 'utf-8')
                }
                return authHeader
            else:
                if self.locale == "cs":
                    QMessageBox.information(None, "Message", "Autorizace nebyla úspěšná! Zkuste to prosím znovu.")
                else:
                    QMessageBox.information(None, "Message", "Autorization was not sucessfull! Please try it again.")                 
                return False
        else:
            return ""         
        
    def fromByteToJson(self, res):
        pom = res
        pom = pom.decode('utf_8')
        try:
            pom = json.loads(pom)
        except:
            if self.locale == "cs":
                msgbox = QMessageBox(QMessageBox.Question, "Layman", "Došlo k chybě při komunikaci se serverem.")
            else:
                msgbox = QMessageBox(QMessageBox.Question, "Layman", "An error occurred while communicating with the server.")
            return

        return pom        
    def removeUnacceptableChars(self, input):
        if input[0] == " ":
            input = input[1:]
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
        input = input.replace(",","")
        input = input.replace(":","")
        input = input.replace("/","_")
        input = input.replace("(","")
        input = input.replace(")","")
        input = input.replace("___","_")
        input = input.replace("__","_")
        input = re.sub(r'[?|$|.|!]',r'',input)
        try:
            if input[len(input) - 1] == "_":
                input = input[:-1]
        except:
            print("removechars exception")
        return input
    def showMessageBar(self, msg, state):
        if self.locale == "cs":
            self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage("Layman:", msg[0]), state, duration=3)
        else:               
            self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage("Layman:", msg[1]), state, duration=3)
    def copyToClipboard(self, data):      
        clipboard = QGuiApplication.clipboard()       
        clipboard.setText(data)        
    def loadWms(self, url, layerName,layerNameTitle, format, epsg, workspace, groupName = '', subgroupName = '', timeDimension='', visibility='', everyone=False, minRes= None, maxRes=0, greyscale = False, legend="0"):               
        layerName = self.parseWMSlayers(layerName) 
        epsg = QgsProject.instance().crs().authid()
        url = url.replace("%2F", "/").replace("%3A",":")
        urlWithParams = 'contextualWMSLegend='+legend+'&crs='+epsg+'&IgnoreReportedLayerExtents=1&dpiMode=7&featureCount=10&format=image/png&layers='+layerName+'&styles=&url=' + url            
        quri = QgsDataSourceUri()
        try:  
            if timeDimension != {}:  
                if 'values' in timeDimension['time']:           
                    print("wmst")             
                    quri.setParam("type", "wmst")
                      #quri.setParam("timeDimensionExtent", "1995-01-01/2021-12-31/PT5M")                        
                    quri.setParam("timeDimensionExtent", str(timeDimension['time']['values']))
                    quri.setParam("allowTemporalUpdates", "true")
                    quri.setParam("temporalSource", "provider")
                            
                else:
                    quri.setParam("type", "wmst")
                    quri.setParam("timeDimensionExtent", self.readDimFromCapatibilites(url, layerName))
                    quri.setParam("allowTemporalUpdates", "true")
                    quri.setParam("temporalSource", "provider")            
        except Exception as e:
            print(e)
            print("error with time wms")
        quri.setParam("layers", layerName.replace("'", ""))
        quri.setParam("styles", '')
        quri.setParam("format", 'image/png')  
        quri.setParam("crs", epsg)
        quri.setParam("dpiMode", '7')
        quri.setParam("featureCount", '10')  
        quri.setParam("IgnoreReportedLayerExtents", '1')   
        if (self.isAuthorized):
            if not everyone:
                quri.setParam("authcfg", self.authCfg)   
        quri.setParam("contextualWMSLegend", legend)
        quri.setParam("url", url)        
        rlayer = QgsRasterLayer(str(quri.encodedUri(), "utf-8").replace("%26","&").replace("%3D","="), layerNameTitle, 'wms')       
        
    
        
        if minRes != None and maxRes != None:
            rlayer.setMinimumScale(self.resolutionToScale(maxRes))
            rlayer.setMaximumScale(self.resolutionToScale(minRes))
            rlayer.setScaleBasedVisibility(True)
        if (groupName != '' or subgroupName != ''):                        
            self.addWmsToGroup(subgroupName,rlayer, "") ## vymena zrusena groupa v nazvu kompozice, nyni se nacita pouze vrstva s parametrem path            
                              
        else:             
            self.loadLayer(rlayer, workspace)  
            self.setVisibility.emit(rlayer)              
        if greyscale:
            rlayer.pipe().hueSaturationFilter().setGrayscaleMode(1)
        return True            
    def checkLayerOnLayman(self, layer_name, workspace, laymanUsername):
        if workspace:
            url = self.URI+'/rest/'+workspace+"/layers/"+layer_name
        else:
            url = self.URI+'/rest/'+laymanUsername+"/layers/"+layer_name
        print(url)
        r = requests.get(url = url, headers = self.getAuthHeader(self.authCfg))        
        try:
            data = r.json()

            if data['wms']['status'] == 'NOT_AVAILABLE' or data['wms']['status'] == 'PENDING':
                return False
            else:
                return True
        except:
            return True # validní vrstva nemá status   
    def parseWMSlayers(self, layerString):
        ### ocekavany string je ve formatu pole napr [vrstva1,vrstva2,...]
        if (layerString[0] == "[" and layerString[-1:] == "]"):
            s = layerString.replace("[","").replace("]","").split(",")
            res = ""
            for i in range(0, len(s)):

                if (i == 0):
                    res = res+ s[i].replace(" ", "") + "&layers="
                elif (i == len(s)-1):
                    res = res+ s[i].replace(" ", "")
                else:
                    res = res+ s[i].replace(" ", "") + "&layers="


            for i in range(0, len(s)-1):
                res = res + "&styles"
            #return res.replace("_","")
            return res
        else:
            return layerString         
    def loadLayer(self, layer, workspace, style = None):
        QgsProject.instance().addMapLayer(layer)

        if (isinstance(layer, QgsVectorLayer)):
            if style is None:                
                # self.loadStyle.emit(layer)
                self._loadStyle(layer, workspace)
            else:                
                style = self.getStyle(layer.name(), style)                    
                layerName = layer.name()
                if (style[0] == 200):
                    if (style[1] == "sld"):
                        tempf = tempfile.gettempdir() + os.sep +self.removeUnacceptableChars(layerName)+ ".sld"
                        layer.loadSldStyle(tempf)
                        layer.triggerRepaint()
                    if (style[1] == "qml"):
                        tempf = tempfile.gettempdir() + os.sep +self.removeUnacceptableChars(layerName)+ ".qml"
                        layer.loadNamedStyle(tempf)
                        layer.triggerRepaint()        
                        
                        
    def _setVisibility(self, layer):                    
        try:
            visibility = self.instance.getVisibilityForLayer(layer.name())
            QgsProject.instance().layerTreeRoot().findLayer(layer).setItemVisibilityChecked(visibility)
        except:
            print("missing visibility parameter")
            QgsProject.instance().layerTreeRoot().findLayer(layer).setItemVisibilityChecked(True)                          
            
    def loadWfs(self, url, layerName,layerNameTitle,workspace, groupName = '', subgroupName = '', visibility= '', everyone=False, minRes= 0, maxRes=None):                    
        layerName = self.removeUnacceptableChars(layerName)        
        epsg = self.iface.mapCanvas().mapSettings().destinationCrs().authid()       
        uri = self.URI+"/geoserver/"+workspace+"/ows?srsname="+epsg+"&typename="+workspace+":"+layerName+"&restrictToRequestBBOX=1&pagingEnabled=True&version=auto&request=GetFeature&service=WFS"
        url = url.replace("%2F", "/").replace("%3A",":").replace("/client","")
        r = url.split("/")
        acc = (r[len(r)-2])
        quri = QgsDataSourceUri()
        quri.setParam("srsname", epsg)
        quri.setParam("typename", acc+":"+layerName)
        quri.setParam("restrictToRequestBBOX", "1")
        quri.setParam("pagingEnabled", "true")
        quri.setParam("version", "auto")
        quri.setParam("request", "GetFeature")
        quri.setParam("service", "WFS")
        if (self.isAuthorized):
            print("add authcfg")
            if not everyone:
                quri.setParam("authcfg", self.authCfg)
        quri.setParam("url", url)
        vlayer = QgsVectorLayer(url+"?" + str(quri.encodedUri(), "utf-8"), layerNameTitle, "WFS")
        print("validity WFS")
        print(vlayer.isValid())
       
            
        if (vlayer.isValid()):         
            if minRes != None and maxRes != None:
                print("set scale")
                vlayer.setMinimumScale(self.resolutionToScale(maxRes))
                vlayer.setMaximumScale(self.resolutionToScale(minRes))
                vlayer.setScaleBasedVisibility(True)
                print(vlayer.hasScaleBasedVisibility())            

            
            if (self.getTypesOfGeom(vlayer) < 2):     
                if (groupName != ''):                    
                    self.addWmsToGroup(groupName,vlayer, subgroupName)

                    self.currentLayer.append(vlayer)                    
                    self.loadStyle.emit(vlayer)
                else:                 
                    self.currentLayer.append(vlayer)
                    # rand = random.randint(0,10000)
                    # self.currentLayerDict[str(rand)] = vlayer     
                    self.loadLayer(vlayer, workspace)    
                    self.setVisibility.emit(vlayer)                       
                    
     
            else: ### cast pro slozenou geometrii
                self.mixedLayers.append(layerName)
                pointFeats = list()
                polyFeats = list()
                lineFeats = list()
                feats = vlayer.getFeatures()       

                pol = 0
                line = 0
                point = 0
                for feat in feats:          
                    if (feat.geometry().type() == 0):
                        pointFeats.append(feat)
                        point = 1

                    if (feat.geometry().type() == 2):
                        polyFeats.append(feat)
                        pol = 1
                    if (feat.geometry().type() == 1):
                        lineFeats.append(feat)
                        line =  1
                if (point == 1):
                    vl = QgsVectorLayer("Point?crs="+epsg, layerName, "memory")
                    pr = vl.dataProvider()
                    pr.addFeatures(pointFeats)
                    vl.updateFields()
                    vl.updateExtents()
                    vl.commitChanges()
                    vl.nameChanged.connect(self.forbidRename)
                    if (groupName != ''):          
                        self.addWmsToGroup(groupName,vl, "")

                    else:
                        self.addLayerToGroup(layerName,vl)                   
                if (line == 1):
                    vl = QgsVectorLayer("LineString?crs="+epsg, layerName, "memory")
                    pr = vl.dataProvider()
                    pr.addFeatures(lineFeats)
                    vl.updateFields()
                    vl.updateExtents()
                    vl.commitChanges()
                    vl.nameChanged.connect(self.forbidRename)
                    if (groupName != ''):
                        self.addWmsToGroup(groupName,vl, True)
                    else:
                        self.addLayerToGroup(layerName,vl)

                if (pol == 1):
                    vl = QgsVectorLayer("Polygon?crs="+epsg, layerName, "memory")
                    pr = vl.dataProvider()
                    pr.addFeatures(polyFeats)
                    vl.updateExtents()
                    vl.updateFields()
                    vl.commitChanges()
                    vl.nameChanged.connect(self.forbidRename)
                    if (groupName != ''):
                        self.addWmsToGroup(groupName,vl, True)
                    else:
                        self.addLayerToGroup(layerName,vl)

            
            return True
        else:
            self.loadLayer(vlayer, workspace) 
            #QgsProject.instance().addMapLayer(vlayer)
            return False            
    def getTypesOfGeom(self, vlayer):
        feats = vlayer.getFeatures()

        typesL = 0
        typesP = 0
        typesPol = 0
        for feat in feats:
            if (typesL == 0):
                if (feat.geometry().type() == 0):
                    typesL = 1
            if (typesP == 0):
                if (feat.geometry().type() == 2):
                    typesP = 1
            if (typesPol == 0):
                if (feat.geometry().type() == 1):
                    typesPol = 1
            if typesL+typesP+typesPol > 2:
                return typesL+typesP+typesPol
        return typesL+typesP+typesPol        
    def _loadStyle(self, layer, workspace):
      
        if (isinstance(layer, QgsVectorLayer)):
            style = self.getStyle(layer.name(), None, workspace)                  
            layerName = layer.name()
            if (style[0] == 200):
                if (style[1] == "sld"):
                    tempf = tempfile.gettempdir() + os.sep +self.removeUnacceptableChars(layerName)+ ".sld"
                    layer.loadSldStyle(tempf)
                    layer.triggerRepaint()
                if (style[1] == "qml"):
                    tempf = tempfile.gettempdir() + os.sep +self.removeUnacceptableChars(layerName)+ ".qml"
                    layer.loadNamedStyle(tempf)
                    layer.triggerRepaint()     
    def getStyle(self, layer_name, style = None, workspace = None):
        if workspace:
            self.selectedWorkspace = workspace
        if style is not None:
            suffix = ".sld"
            self.saveExternalStyle(style, layer_name)     
            return 200, suffix.replace(".","")
        if self.selectedWorkspace:
            response = requests.get(self.URI+'/rest/'+self.selectedWorkspace+'/layers/' + self.removeUnacceptableChars(layer_name)+ '/style', headers = self.getAuthHeader(self.authCfg))
            #response = self.requestWrapper("GET", self.URI+'/rest/'+self.selectedWorkspace+'/layers/' + self.removeUnacceptableChars(layer_name)+ '/style', payload = None, files = None)
        else:
            #response = self.requestWrapper("GET", self.URI+'/rest/'+self.laymanUsername+'/layers/' + self.removeUnacceptableChars(layer_name)+ '/style', payload = None, files = None)
            response = requests.get(self.URI+'/rest/'+self.laymanUsername+'/layers/' + self.removeUnacceptableChars(layer_name)+ '/style', headers = self.getAuthHeader(self.authCfg))      
        res = response.content
        res = res.decode("utf-8")
        if (res[0:5] == "<qgis" and response.status_code == 200):
            print("got qml")
            suffix = ".qml"

        if (res[0:5] == "<?xml" and response.status_code == 200):
            print("got sld")
            suffix = ".sld"
        try:
            tempf = tempfile.gettempdir() + os.sep +self.removeUnacceptableChars(layer_name) + suffix
        except:
            print("symbologie nenalezena")
            return (400,"")
        
        with open(tempf, 'wb') as f:
            f.write(response.content)                 
        return response.status_code, suffix.replace(".","")                    
    def getUserName(self):       
        userEndpoint = self.URI+ "/rest/current-user"        
        r = self.requestWrapper("GET", userEndpoint, payload = None, files = None)
        res = self.fromByteToJson(r.content) 
        return res['username']
    
    def getUserFullName(self):
        userEndpoint = self.URI+ "/rest/current-user"  
        r = self.requestWrapper("GET", userEndpoint, payload = None, files = None)
        res = self.fromByteToJson(r.content)
        print(res)
        return res['claims']['name']
    
    
    def listToString(self, s):

        str1 = ","
        return (str1.join(s))
    def convertUrlFromHex(self, url):
        url = url.replace('%3A',':')
        url = url.replace('%2F','/')
        url = url.replace('%3F','?')
        url = url.replace('%3D','=')
        url = url.replace('%26','&')
        return url
    def hasLaymanLayer(self, name, workspace):
        url = self.URI + "/rest/"+workspace+"/maps/"+name+"/file"
        r = self.requestWrapper("GET", url, payload = None, files = None)
        composition = r.json()
        for layer in composition['layers']:
            if layer['className'] == "OpenLayers.Layer.Vector":
                if '/geoserver/' in layer['protocol']['url']:
                    return True
            if layer['className'] == "HSLayers.Layer.WMS":
                if '/geoserver/' in layer['url']:
                    return True
        return False
    def checkExistingLayer(self, layerName):
        layerName = self.removeUnacceptableChars(layerName)
        url = self.URI+'/rest/'+self.laymanUsername+"/layers"
        r = self.requestWrapper("GET", url, payload = None, files = None)      
        if not r:
            return
        data = r.json()

        pom = set()
        for x in range(len(data)):
            pom.add((data[x]['name']))
        layerName = layerName.replace(" ", "_").lower()     
        if (layerName in pom):
            return True
        else:
            return False
    def checkExistingLayers(self, layerName):
        layerName = self.removeUnacceptableChars(layerName)
        url = self.URI+'/rest/layers'
        r = self.requestWrapper("GET", url, payload = None, files = None)      
        if not r:
            return
        data = r.json()

        pom = set()
        for x in range(len(data)):
            pom.add((data[x]['name']))
        layerName = layerName.replace(" ", "_").lower()     
        if (layerName in pom):
            return True
        else:
            return False        
    def fillCompositionDict(self):
        compositionDict = {}
        url = self.URI+'/rest/maps'
        r = requests.get(url = url, headers = self.getAuthHeader(self.authCfg))
        dataAll = r.json()
        for row in range(0, len(dataAll)):
            compositionDict[dataAll[row]['name']] = dataAll[row]['title']       
        return compositionDict               
    def wgsToKrovak(self, x, y):
        src = QgsCoordinateReferenceSystem(5514)
        dest = QgsCoordinateReferenceSystem(4326)
        tform = QgsCoordinateTransform(src, dest, QgsProject.instance())
        point = tform.transform(QgsPointXY(x, y))
        return [point.x(), point.y()]
    def krovakToWgs(self, x, y):
        src = QgsCoordinateReferenceSystem(4326)
        dest = QgsCoordinateReferenceSystem(5514)
        tform = QgsCoordinateTransform(src, dest, QgsProject.instance())
        point = tform.transform(QgsPointXY(x, y))
        return [point.x(), point.y()]
    def isPathAbsolute(self, path):
        return os.path.isabs(path)
    def getSvgPath(self):
        return QgsApplication.prefixPath() + '/svg/'
    def getSource(self, layer):
        uri = layer.dataProvider().uri().uri()
        if ".geojson" in uri:
            return "GEOJSON"
        elif ".shp" in uri:
            return "SHP"
        elif "wms" in uri:
            return "WMS"
        elif "wfs" in uri:
            return "WFS"
        elif str(layer.providerType()) == "memory":
            return "MEMORY"
        elif str(layer.providerType()) == "gdal":

            return "RASTER"
        else:
            return "OGR"
    def resolutionToScale(self, resolution):
        map_settings = self.iface.mapCanvas().mapSettings()
        crs = map_settings.destinationCrs()        
        dpi = 25.4 / 0.28  #  96 dpi         
        if resolution < 0.72: ##  hranice spatneho zaorouhleni
            return round(resolution * 39.37 * dpi, -3)
        else:
            return self.resolutionRounder(round(resolution * 39.37 * dpi))        
        
    def scaleToResolution(self, denominator):   
        map_settings = self.iface.mapCanvas().mapSettings()
        crs = map_settings.destinationCrs()
        units = crs.mapUnits()
        dpi = 25.4 / 0.28
        mpu = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, units)    
        return denominator / (mpu * 39.37 * dpi)    

    def resolutionRounder(self,x):
        rounded = int(round(x / 5000.0) * 5000)
        power = len(str(rounded)) - 1
        first_digit = int(str(rounded)[0])
        return first_digit * 10**power        
    def showQgisBar(self, msg, type):   
        if self.locale == "cs":
            self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage("Layman:", msg[0]), type, duration=3)
        else:
            self.iface.messageBar().pushWidget(self.iface.messageBar().createMessage("Layman:", msg[1]), type, duration=3) 
    def find_substring(self, searchable_str, start_str, stop_str):
        start_index = searchable_str.find(start_str)  
        if start_index == -1:  #
            return None
        start_index += len(start_str)  
        end_index = searchable_str.find(stop_str, start_index)  
        if end_index == -1: 
            return None
        return searchable_str[start_index:end_index]             
    def isLayerPostgres(self, layer):
        provider = layer.dataProvider()
        print(provider.name())
        if provider.name() == "postgres":
            return True
        else:
            return False 
    def get_raster_min_max(self,raster_layer):  
        extent = raster_layer.extent()  
        provider = raster_layer.dataProvider()
        stats = provider.bandStatistics(1, QgsRasterBandStats.All, extent, 0)
        min_val, max_val = stats.minimumValue, stats.maximumValue
        return min_val, max_val
    def checkPublicationStatus(self, layer):        
        url = self.URI+'/rest/'+self.laymanUsername+'/layers/'+layer
        print(url)
        r = requests.get(url, headers = self.getAuthHeader(self.authCfg))
        print(r.content)
        response = self.fromByteToJson(r.content) 
        if not 'layman_metadata' in response:
            return False
        if response['layman_metadata'] == 'COMPLETE':
            return True
        else:
            return False
    def isBinaryRaster(self,raster_layer):
        min_val, max_val = self.get_raster_min_max(raster_layer)
        print(min_val, max_val)
        if min_val == 0 and max_val == 1:
            return True
        else:
            return False        
    def apply_button_stylesheet(self):
        # Define the common stylesheet for the QPushButtons
        
        button_stylesheet = '''
        QPushButton {
    text-align: left;
    padding-left: 20px; /* Odsazení pro ikonu */
}

QPushButton::indicator {
    width: 50px; /* Šířka ikony */
    height: 50px; /* Výška ikony */
}

    '''

        for widget in QApplication.instance().allWidgets():
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(button_stylesheet)        
    def csvToArray(self, path):
        results = []
        with open(path) as csvfile:
            reader = csv.reader(csvfile,delimiter=',') # change contents to floats
            for row in reader: # each row is a list
                results.append(row)
        return results      
    def loadIni(self):
        file =  os.getenv("HOME") + os.sep + ".layman" + os.sep +'layman_user.INI'
        config = configparser.ConfigParser()
        config.read(file)
        return config  
    
    def checkWgsExtent(self, layer):
        WgsXmax = 180
        WgsXmin = -180
        WgsYmax = 90
        WgsYmin = -90
        extent = layer.extent()
        if (extent.xMaximum() > WgsXmax or extent.xMinimum() < WgsXmin or extent.yMaximum() > WgsYmax or extent.yMinimum() < WgsYmin ):
            return False
        else:
            return True
        
    def _onEmitMessageBox(self, message):    
        if self.locale == "cs":
            QMessageBox.information(None, "Layman", message[0])
        else:
            QMessageBox.information(None, "Layman", message[1])              
    def set_icon_size_for_all_buttons(self, container):       
        css = f"QPushButton {{ background-image: url(''); background-size: 5px 5px; }}"   
        for widget in container.findChildren(QPushButton):
            widget.setStyleSheet(css)
    def compare_json_layers(self, schema1, schema2):
        layers1 = schema1["layers"]
        layers2 = schema2["layers"]      
        layer_names1 = set(layer["title"] for layer in layers1)
        layer_names2 = set(layer["title"] for layer in layers2)
        print(layer_names1, layer_names2)
        # Rozdíl mezi názvy vrstev
        extra_layers1 = layer_names1 - layer_names2
        extra_layers2 = layer_names2 - layer_names1

        if extra_layers1:
            print(f"Ve schématu jedna ubyly tyto vrstvy oproti schématu dva: {', '.join(extra_layers1)}")
            return True
        if extra_layers2:
            print(f"Ve schématu jedna přibyly tyto vrstvy oproti schématu dva: {', '.join(extra_layers2)}")
            return True
        if not extra_layers1 and not extra_layers2:
            print("Všechny vrstvy jsou shodné mezi oběma schématy.")
            return False
        return [extra_layers1, extra_layers2]
    def decode_url(self, encoded_url):
        decoded_url = urllib.parse.unquote(encoded_url)
        return decoded_url
class ProxyStyle(QtWidgets.QProxyStyle):    
    def drawControl(self, element, option, painter, widget=None):
        if element == QtWidgets.QStyle.CE_PushButtonLabel:
            icon = QtGui.QIcon(option.icon)
            option.icon = QtGui.QIcon()     
        super(ProxyStyle, self).drawControl(element, option, painter, widget)
        if element == QtWidgets.QStyle.CE_PushButtonLabel:
            if not icon.isNull():
                iconSpacing = 4
                mode = (
                    QtGui.QIcon.Normal
                    if option.state & QtWidgets.QStyle.State_Enabled
                    else QtGui.QIcon.Disabled
                )
                if (
                    mode == QtGui.QIcon.Normal
                    and option.state & QtWidgets.QStyle.State_HasFocus
                ):
                    mode = QtGui.QIcon.Active
                state = QtGui.QIcon.Off
                if option.state & QtWidgets.QStyle.State_On:
                    state = QtGui.QIcon.On
                window = widget.window().windowHandle() if widget is not None else None   
                size = PyQt5.QtCore.QSize(15, 15)
                pixmap = icon.pixmap(window, size, mode, state)
                pixmapWidth = pixmap.width() / pixmap.devicePixelRatio()
                pixmapHeight = pixmap.height() / pixmap.devicePixelRatio()
                iconRect = QtCore.QRect(
                    QtCore.QPoint(), QtCore.QSize(int(pixmapWidth), int(pixmapHeight))
                )
                iconRect.moveCenter(option.rect.center())
                iconRect.moveLeft(option.rect.left() + iconSpacing)
                iconRect = self.visualRect(option.direction, option.rect, iconRect)
                iconRect.translate(
                    self.proxy().pixelMetric(
                        QtWidgets.QStyle.PM_ButtonShiftHorizontal, option, widget
                    ),
                    self.proxy().pixelMetric(
                        QtWidgets.QStyle.PM_ButtonShiftVertical, option, widget
                    ),
                )
                painter.drawPixmap(iconRect, pixmap)                 
                