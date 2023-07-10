import json
import requests
import configparser
import os
from qgis.core import *
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QByteArray, Qt
import io
from PyQt5.QtNetwork import  QNetworkRequest
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox
from .dlg_errMsg import ErrMsgDialog
class LaymanUtils(QObject): 
    showErr = pyqtSignal(list,str,str,Qgis.MessageLevel, str)    
    def __init__(self, iface, locale,  parent=None):
        super(LaymanUtils, self).__init__(parent=parent)
        self.plugin_dir = os.path.dirname(__file__)
        self.isAuthorized = False
        self.URI = ""
        self.locale = locale
        self.iface = iface
        
    def connectEvents(self):         
        self.showErr.connect(self.showMessageBar)
        
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
            self.showErr.emit(["Požadavek nebyl úspěšný", "Request was not successfull"], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)    
        return response        
           
    def recalculateDPI(self):
        self.DPI = self.getDPI()
        if self.DPI < 0.85:
            self.fontSize = "12px"
        else:
            self.fontSize = "10px"  
            
    def showMessageBar(self, text, info, err, typ, url):    
        print("krysodals")
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