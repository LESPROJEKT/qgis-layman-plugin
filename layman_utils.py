import json
import requests
import configparser
import os
import re
from qgis.core import *
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QByteArray, Qt
import io
from PyQt5.QtNetwork import  QNetworkRequest
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox
from .dlg_errMsg import ErrMsgDialog
import tempfile
class LaymanUtils(QObject): 
    showErr = pyqtSignal(list,str,str,Qgis.MessageLevel, str)  
    setVisibility = pyqtSignal(QgsMapLayer)
    loadStyle = pyqtSignal(QgsMapLayer)
      
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
               
    def requestWrapper(self, type, url, payload = None, files = None):       
        try:
            response = requests.request(type, url = url, headers=self.getAuthHeader(self.authCfg), data=payload, files=files) 
        except Exception as ex:   
            info = str(ex)            
            self.showErr.emit(["Připojení není k dispozici","Connection is not available"],info, str(info), Qgis.Warning, "")                
            return
        print(response.status_code)
        if response.status_code != 200: 
            print(url)
            self.showErr.emit(["Požadavek nebyl úspěšný", "Request was not successfull"], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)    
        return response        
           
    def recalculateDPI(self):
        self.DPI = self.getDPI()
        if self.DPI < 0.85:
            self.fontSize = "12px"
        else:
            self.fontSize = "10px"  
            
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
        r = requests.get("https://gitlab.com/plan4all/layman-qgis-plugin/-/raw/master/metadata.txt?inline=false")
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
            xx = QNetworkRequest(url)   
            i = 0
            success = (QgsApplication.authManager().updateNetworkRequest(xx, authCfg))      
            if success[0] == True:
                header = (xx.rawHeader(QByteArray(b"Authorization")))                
                authHeader ={
                  "Authorization": str(header, 'utf-8')
                }
                return authHeader
            else:
                if self.locale == "cs":
                    QMessageBox.information(None, "Message", "Autorizace nebyla úspěšná! Prosím zkuste to znovu.")
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