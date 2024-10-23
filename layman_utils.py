import json
import requests
import configparser
import os
import re
import PyQt5
from qgis.core import *
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QByteArray, Qt, QRect, QSize
import io
from PyQt5.QtNetwork import  QNetworkRequest
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox, QApplication, QStyledItemDelegate
from qgis.PyQt.QtGui import QGuiApplication
from .dlg_errMsg import ErrMsgDialog
import tempfile
from PyQt5 import QtWidgets, QtGui, QtCore
import csv
import http.client
import asyncio
import ssl
import urllib.parse
import base64
import imghdr
import io
import hashlib
from datetime import datetime, timedelta
import math
from qgis.PyQt.QtGui import QImage
from qgis.PyQt.QtCore import QSize
import processing


class LaymanUtils(QObject): 
    showErr = pyqtSignal(list,str,str,Qgis.MessageLevel, str)  
    setVisibility = pyqtSignal(QgsMapLayer)
    loadStyle = pyqtSignal(QgsMapLayer)
    emitMessageBox = pyqtSignal(list)
    showQBar = pyqtSignal(list,Qgis.MessageLevel)
    showMessageSignal = pyqtSignal(list, int)
      
    def __init__(self, iface, locale,laymanUsername,  parent=None):
        super(LaymanUtils, self).__init__(parent=parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.isAuthorized = False
        self.URI = ""
        self.locale = locale
        self.iface = iface
        self.laymanUsername = laymanUsername
        self.currentLayer = []
        self.showMessageSignal.connect(self.showQgisBar)
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
               
    def requestWrapper(self, type, url, payload = None, files = None, emitErr = True, additionalHeaders = None):       
        try:
            if additionalHeaders is None:
                response = requests.request(type, url = url, headers=self.getAuthHeader(self.authCfg), data=payload, files=files) 
            else:
                response = requests.request(type, url = url, headers={**self.getAuthHeader(self.authCfg), **additionalHeaders}, data=payload, files=files)                 
        except Exception as ex:   
            info = str(ex)    
            if emitErr:        
                self.showErr.emit(["Připojení není k dispozici","Connection is not available"],info, str(info), Qgis.Warning, "")  
            return       
        if emitErr:
            if response.status_code not in (200, 201): 
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
    def setTableWidgetNotBorder(self, widget):
        widget.setStyleSheet("""
    QTableWidget {
        border: none;
        gridline-color: transparent;
    }
    QTableWidget::item {
        border: none;
    }
    QTableWidget::item:focus {
        border: none;
        outline: none;
    }
    """)          
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
            url = QUrl(self.URI+ "/rest/current-user")
            req = QNetworkRequest(url)    
            success = QgsApplication.authManager().updateNetworkRequest(req, authCfg)                 
            if success[0] == True:
                header = (req.rawHeader(QByteArray(b"Authorization")))  
                authHeader ={
                  "Authorization": str(header, 'utf-8'),
                  "X-Client": "LAYMAN",                  
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
                QMessageBox(QMessageBox.Question, "Layman", "Došlo k chybě při komunikaci se serverem.")
            else:
                QMessageBox(QMessageBox.Question, "Layman", "An error occurred while communicating with the server.")
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
            self.addWmsToGroup(subgroupName,rlayer, "")           
                              
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
        else:            
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
    def getLayers(self):   
        url = self.URI+'/rest/layers'
        r = self.requestWrapper("GET", url, payload = None, files = None)      
        if not r:
            return
        data = r.json()     
        return data
        
    def checkExistingLayers(self, layerName, data):
        layerName = self.removeUnacceptableChars(layerName)        
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
    def checkIfNotLocalLayer(self):
        project = QgsProject.instance()
        layers = project.mapLayers().values()
        accepted_data_providers = ['wms', 'WFS']
        layer_found = any(layer.dataProvider().name() not in accepted_data_providers for layer in layers)
        if layer_found:
            return True
        else:
            return False     
    def removeWmsWfsLayers(self):        
        projekt = QgsProject.instance()      
        seznam_vrstev = projekt.mapLayers().values()  
        for vrstva in seznam_vrstev:
            if isinstance(vrstva, (QgsVectorLayer, QgsRasterLayer)):            
                provider = vrstva.dataProvider().name()            
                if 'wms' in provider or 'WFS' in provider:               
                    projekt.removeMapLayer(vrstva)        
    def compare_json_layers(self, schema1, schema2):
        layers1 = schema1["layers"]
        layers2 = schema2["layers"]      
        layer_names1 = set(layer["title"] for layer in layers1)
        layer_names2 = set(layer["title"] for layer in layers2)
        layer_canvas = set([layer.name() for layer in QgsProject.instance().mapLayers().values()])
        print(layer_names1, layer_names2)
        # Rozdíl mezi názvy vrstev
        extra_layers1 = layer_names1 - layer_names2
        extra_layers2 = layer_names2 - layer_names1
        canvas_state = layer_canvas - layer_names2
        canvas_state2 =  layer_names2 - layer_canvas
        if extra_layers1:
            print(f"Ve schématu jedna ubyly tyto vrstvy oproti schématu dva: {', '.join(extra_layers1)}")
            return True
        if extra_layers2:
            print(f"Ve schématu jedna přibyly tyto vrstvy oproti schématu dva: {', '.join(extra_layers2)}")
            return True
        if not extra_layers1 and not extra_layers2:
            if len(canvas_state) != len(canvas_state2):          
                return True           
            else:
                print("Všechny vrstvy jsou shodné mezi oběma schématy.")
                return False
        return [extra_layers1, extra_layers2]
    def decode_url(self, encoded_url):
        decoded_url = urllib.parse.unquote(encoded_url)
        return decoded_url
    def extractFileTypeFromBaseImage(self, base64_image):
        base64_image = base64_image.replace("base64:","")
        image_data = base64.b64decode(base64_image)        
        if b'<svg' in image_data[:1000]:
            mime_type = "data:image/svg+xml"
        else:            
            file_type = imghdr.what(io.BytesIO(image_data))       
            mime_type_mapping = {
                "jpeg": "data:image/jpeg",
                "png": "data:image/png",
                "gif": "data:image/gif",
                "bmp": "data:image/bmp",
                "tiff": "data:image/tiff"
            }            
            mime_type = mime_type_mapping.get(file_type, "data:unknown")
        return mime_type   
    
    def generate_md5(self, filename):
        hash_md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    def generate_sha256(self, filename):
        hash_sha256 = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    def create_local_files_hash_dict(self, directory):        
        files_hashes = {}
        for filename in os.listdir(directory):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path):
                files_hashes[full_path] = self.generate_md5(full_path)
        return files_hashes
    
    def get_filename_with_extension(self, full_path):
        filename_with_extension = os.path.basename(full_path)       
        return filename_with_extension
    
    def get_filename_without_extension(self, full_path):
        filename_with_extension = os.path.basename(full_path)
        filename_without_extension, _ = os.path.splitext(filename_with_extension)
        return filename_without_extension
    def getUserScreenNames(self):       
        usersEndpoint = self.URI + "/rest/users"   
        r = self.requestWrapper("GET", usersEndpoint, payload=None, files=None)   
        res = self.fromByteToJson(r.content)  
        user_screen_names = {}    
        for user in res:   
            user_screen_names[user['username']] = user['screen_name']           
        return user_screen_names
    def saveUnsavedLayers(self):    
        project = QgsProject.instance()   
        for layer in project.mapLayers().values():        
            if layer.type() == QgsMapLayer.VectorLayer and layer.isModified():           
                if layer.commitChanges():
                    print(f"Changes saved for layer: {layer.name()}")
                else:
                    print(f"Failed to save changes for layer: {layer.name()}")
            else:            
                print(f"No changes to save or not a vector layer: {layer.name()}")
    def transformUsernames(self, search_names):        
        user_screen_names = self.getUserScreenNames()
        result = []
        for name in search_names:
            if name.isupper():               
                result.append(name)
            else:                
                result.append(user_screen_names.get(name, name))
        return result
    def findCommonUsers(self, usernames, qfield_users): 
        usernames_set = set(usernames)      
        common_users = []
        for user in qfield_users:
            if user['username_display'] in usernames_set:
                common_users.append(user['username_display'])
        return common_users      
    def isWmsOrWfs(self, layer):
        return layer.providerType() in ['wms', 'wfs']
    
    def containsWmsOrWfs(self):
        project = QgsProject.instance()     
        layers = project.mapLayers().values()
        for layer in layers:
            if self.isWmsOrWfs(layer):            
                return True
        return False
    def getWmsOrWfsLayers(self):        
        project = QgsProject.instance()
        layers = project.mapLayers().values()   
        wms_wfs_layers = [layer for layer in layers if self.isWmsOrWfs(layer)]        
        return wms_wfs_layers
    
    def hasMatchingLayer(self, wms_wfs_layers, response_data):          
        layer_names = [layer.name() for layer in wms_wfs_layers]
        for item in response_data:
            item_name_without_extension = os.path.splitext(item["name"])[0]         
            if item_name_without_extension in layer_names:
                return True
        return False
    
    def filterTitlesByAccessRights(self, layers):
        url = self.URI + '/rest/' + self.laymanUsername + '/layers'
        response = requests.get(url, headers=self.getAuthHeader(self.authCfg))        
        filtered_layers = []  
        for layer in response.json():
            read_rights = layer.get('access_rights', {}).get('read', [])
            write_rights = layer.get('access_rights', {}).get('write', [])
            
            if "EVERYONE" not in read_rights and "EVERYONE" not in write_rights:
                if layer['title'] in layers:                    
                    filtered_layers.append({
                        'title': layer['title'],
                        'access_rights': {
                            'read': read_rights,
                            'write': write_rights
                        }
                    })
        
        return filtered_layers
    def updateLayerAccessRights(self, filtered_layers):       
        for layer in filtered_layers:
            title = layer['title']            
            title = self.removeUnacceptableChars(title)         
            url = f"{self.URI}/rest/{self.laymanUsername}/layers/{title}"         
            read_access = layer['access_rights']['read'] + ['EVERYONE']
            write_access = layer['access_rights']['write'] + ['EVERYONE']           
            data = {
                'access_rights.read': self.listToString(read_access),
                'access_rights.write': self.listToString(write_access)
            }        
            response = requests.patch(url, data=data, headers=self.getAuthHeader(self.authCfg))
            print(f"Update for layer '{title}': {response.status_code}, Response: {response.text}")

    def removeAuthcfg(self, json_layers):               
        layer_data = json.loads(json_layers) if isinstance(json_layers, str) else json_layers  
        layers_to_update = [layer['title'] for layer in layer_data]
        project = QgsProject.instance()    
        for layer in project.mapLayers().values():           
            if layer.name() in layers_to_update:          
                original_url = layer.source()               
                parts = original_url.split("&")               
                filtered_parts = [part for part in parts if not part.startswith("authcfg=")]              
                new_url = "&".join(filtered_parts)              
                layer.setDataSource(new_url, layer.name(), layer.providerType())

    def compareUpdates(self, qfieldUpdate, laymanUpdate):      
        json_obj1 = json.loads(qfieldUpdate)
        json_obj2 = json.loads(laymanUpdate)        
        created_at1 = datetime.fromisoformat(json_obj1['created_at'])
        updated_at1 = datetime.fromisoformat(json_obj1['updated_at'])
        updated_at2 = datetime.fromisoformat(json_obj2['updated_at'])        
        if updated_at1 != created_at1:         
            time_difference = updated_at2 - updated_at1
            if time_difference >= timedelta(minutes=3):
                return "Informace: První updated_at je starší nebo rovno 3 minutám oproti druhému updated_at."
            else:
                return "Informace: První updated_at není starší než 3 minuty oproti druhému updated_at."
        else:
            return "Informace: updated_at a created_at v prvním JSON objektu jsou stejné."       


    def compareLayers(qfieldFiles, laymanLayers, layersInProject):       
        qfieldFiles = json.loads(qfieldFiles)
        laymanLayers = json.loads(laymanLayers)    
        layer_dict2 = {layer['title']: layer for layer in laymanLayers if layer['title'] in layersInProject}   
        for layer1 in qfieldFiles:
            name1 = layer1['name']       
            if name1.endswith('.gpkg'):
                base_name1 = name1.rsplit('.', 1)[0]  
                last_modified1_str = layer1['last_modified']
                last_modified1 = datetime.strptime(last_modified1_str, "%d.%m.%Y %H:%M:%S UTC")               
                if base_name1 in layer_dict2:
                    layer2 = layer_dict2[base_name1]
                    updated_at2_str = layer2['updated_at']
                    updated_at2 = datetime.fromisoformat(updated_at2_str.replace("Z", "+00:00"))              
                    time_difference = updated_at2 - last_modified1
                    if time_difference >= timedelta(minutes=3):
                        print(f"Informace: last_modified vrstvy '{name1}' je starší nebo rovno 3 minutám oproti updated_at vrstvy '{base_name1}'.")
                    else:
                        print(f"Informace: last_modified vrstvy '{name1}' není starší než 3 minuty oproti updated_at vrstvy '{base_name1}'.")
                else:
                    print(f"Informace: Vrstva s názvem '{base_name1}' nebyla nalezena ve druhém seznamu.")

    def getLayersFromCanvas(self):
        project = QgsProject.instance()
        layers = project.mapLayers().values()
        layer_names = [layer.name() for layer in layers]
        return layer_names

    def getLayersFromComposition(self, name):
        url = self.URI+'/rest/'+self.laymanUsername+'/maps/'+name+'/file'                
        r = self.utils.requestWrapper("GET", url, payload = None, files = None)
        if r is not None:
            data = r.json()
            layers = [layer['title'] for layer in data.get('layers', [])]
            return layers
        else:
            return []   
    def downloadFile(self, url, local_filename):
        headers = self.getAuthHeader(self.authCfg)
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk) 
    def openQgisProject(self, project_path):        
        project = QgsProject.instance()
        project_path = self.findQgisProject(project_path)
        project.read(project_path)   

    def findQgisProject(self, directory):
        """Najde první .qgz nebo .qgs soubor v zadaném adresáři."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.qgz') or file.endswith('.qgs'):
                    return os.path.join(root, file)
        return None
    
    def estimateMbtilesSizeWmsLayer(self, active_layer, min_zoom=14, max_zoom=16, avg_tile_size_kb=10, dpi=96): 
        extent = self.iface.mapCanvas().extent()
        dpi_adjustment_factor = dpi / 96.0       
        tile_size = 256 * dpi_adjustment_factor  
        total_tiles = 0       
        for zoom in range(min_zoom, max_zoom + 1):            
            tile_count_x = math.ceil(extent.width() / (tile_size / (2 ** zoom)))
            tile_count_y = math.ceil(extent.height() / (tile_size / (2 ** zoom)))
            total_tiles += tile_count_x * tile_count_y       
        compression_factor = 0.1  
        estimated_size_MB = total_tiles * avg_tile_size_kb * compression_factor / 1024
        return estimated_size_MB
    
    def estimateSizeFromScale(self, scale, base_scale=1885, base_size_mb=1.8, scale_multiplier=3):    
        scale_factor = scale / base_scale
        zoom_levels_away = math.log(scale_factor, 2)   
        estimated_size = base_size_mb * (scale_multiplier ** zoom_levels_away)
        return estimated_size

    def checkLayerSize(self, size_threshold_mb=100):
        project = QgsProject.instance()
        layers = project.mapLayers().values() 
        found_large_layer = False 
        for layer in layers:
            if isinstance(layer, QgsRasterLayer):
                if layer.providerType() in ['wms', 'xyz']:     
                    scale = self.iface.mapCanvas().scale()
                    estimated_size = self.estimateSizeFromScale(scale)
                    if estimated_size > size_threshold_mb:
                        print(f"Vrstva '{layer.name()}' má odhadovanou velikost {estimated_size:.2f} MB, což přesahuje limit {size_threshold_mb} MB.")
                        found_large_layer = True  
        return found_large_layer
    
    def export_layer_to_tiff(self, layer, output_file, dpi=300):      
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        map_settings = QgsMapSettings()
        map_settings.setLayers([layer])
        map_settings.setExtent(extent)
        map_settings.setOutputDpi(dpi) 
        canvas_size = canvas.size()
        image_width = canvas_size.width()
        image_height = canvas_size.height()
        map_settings.setOutputSize(QSize(image_width, image_height))     
        renderer = QgsMapRendererParallelJob(map_settings)
        renderer.start()
        renderer.waitForFinished()
        image = renderer.renderedImage()       
        success = image.save(output_file, "tif")
        if success:
            print(f"TIFF pro vrstvu {layer.name()} byl uložen do {output_file}")
            return True
        else:
            print(f"Chyba při ukládání TIFF pro vrstvu {layer.name()}")
            return False

    def export_layer_to_mbtiles(self, layer, output_directory, file_name, min_zoom=14, max_zoom=16, dpi=100):   
        extent = self.iface.mapCanvas().extent()  
        output_file = os.path.join(output_directory, f"{file_name}.mbtiles")
        
        params = {
            'LAYERS': [layer.id()],
            'EXTENT': extent,
            'ZOOM_MIN': min_zoom,
            'ZOOM_MAX': max_zoom,
            'DPI': dpi,
            'BACKGROUND_COLOR': 'transparent',
            'TILE_FORMAT': 0,
            'QUALITY': 80,
            'METATILESIZE': 4,
            'TITLE': f'MBTiles Layer {layer.name()}',
            'TMS_CONVENTION': False,
            'OUTPUT_FILE': output_file
        }
        
        processing.run('qgis:tilesxyzmbtiles', params)
        print(f"MBTiles soubor pro vrstvu {layer.name()} byl uložen na: {output_file}")
        return output_file
    def replace_wms_xyz_layers(self, output_format='tiff'):    
        project = QgsProject.instance()
        layers = project.mapLayers().values()     
        temp_dir = tempfile.mkdtemp()      
        layers_to_remove = []
        layers_to_add = []

        for layer in layers:     
            if isinstance(layer, QgsRasterLayer):
                provider_type = layer.providerType()
                if provider_type in ["wms", "wmsprovider", "wms_client", "xyz"]:   
                    file_name = layer.name().replace(" ", "_")                    
                    if output_format == 'tiff':
                        output_file = os.path.join(temp_dir, f"{file_name}.tif")
                        success = self.export_layer_to_tiff(layer, output_file)
                    elif output_format == 'mbtiles':
                        output_file = self.export_layer_to_mbtiles(layer, temp_dir, file_name)
                        print(output_file)                      
                        success = True if output_file else False
                    
                    if success:
                        layers_to_remove.append(layer.id())
                        if output_format == 'tiff':
                            tiff_layer = QgsRasterLayer(output_file, layer.name())
                            if tiff_layer.isValid():
                                layers_to_add.append(tiff_layer)
                            else:
                                print(f"Chyba při vytváření vrstvy z TIFF pro {layer.name()}")
                        elif output_format == 'mbtiles':                          
                            mbtiles_layer = QgsRasterLayer(output_file, layer.name())
                            if mbtiles_layer.isValid():
                                layers_to_add.append(mbtiles_layer)
                            else:
                                print(f"Chyba při načítání MBTiles vrstvy pro {layer.name()}")
                    else:
                        print(f"Chyba při exportu vrstvy {layer.name()} do {output_format.upper()}")
                else:
                    print(f"Přeskakuji vrstvu {layer.name()} (poskytovatel: {provider_type})")
            else:
                print(f"Přeskakuji nerastrovou vrstvu {layer.name()}")       
 
        for layer_id in layers_to_remove:
            layer = project.mapLayer(layer_id)
            project.removeMapLayer(layer)

       
        for new_layer in layers_to_add:
            project.addMapLayer(new_layer)
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
                              

class IconQfieldDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):   
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        text = index.model().data(index, QtCore.Qt.DisplayRole)
        icon = index.model().data(index, QtCore.Qt.DecorationRole)      
        if text:
            painter.save()
            painter.drawText(option.rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, text)
            painter.restore()      
        if icon and index.column() == 0:  
            space = 5 
            text_width_with_space = option.fontMetrics.width(text) + space
            icon_size = QtCore.QSize(14, 14)
            icon_x = int(option.rect.left() + text_width_with_space)
            icon_y = int(option.rect.center().y() - icon_size.height() / 2)           
            icon_rect = QtCore.QRect(icon_x, icon_y, icon_size.width(), icon_size.height())           
            painter.save()
            painter.setClipRect(option.rect)  
            icon.paint(painter, icon_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            painter.restore()



class IconQfieldRightDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):           
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())  
        text = index.model().data(index, QtCore.Qt.DisplayRole)
        icon = index.model().data(index, QtCore.Qt.DecorationRole)     
        if text:
            painter.save()
            painter.drawText(option.rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, text)
            painter.restore()       
        if icon and index.column() == 0:  
            icon_size = QtCore.QSize(14, 14) 
            icon_x = int(option.rect.right() - icon_size.width())  
            icon_y = int(option.rect.center().y() - icon_size.height() / 2)  
            icon_rect = QtCore.QRect(icon_x, icon_y, icon_size.width(), icon_size.height())          
            painter.save()
            icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter)
            painter.restore()


class CenterIconDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        icon = index.data(Qt.DecorationRole)
        if icon:         
            iconSize = QSize(14, 14)            
            iconX = round(option.rect.left() + (option.rect.width() - iconSize.width()) / 2)
            iconY = round(option.rect.top() + (option.rect.height() - iconSize.height()) / 2)
            iconRect = QRect(iconX, iconY, iconSize.width(), iconSize.height())             
            icon.paint(painter, iconRect, Qt.AlignCenter)
        else:
            super().paint(painter, option, index)

