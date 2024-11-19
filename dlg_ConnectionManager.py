# -*- coding: utf-8 -*-
"""
/***************************************************************************
                                 A QGIS plugin
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-03-19
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Jan Vrobel
        email                : vrobel.jan@seznam.cz
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import uic
from PyQt5 import QtWidgets
from .layman_utils import ProxyStyle
from qgis.core import  QgsSettings, QgsApplication, QgsProject
from PyQt5.QtWidgets import QPushButton
import threading

                             

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dlg_ConnectionManager.ui'))


class ConnectionManagerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self,utils, server, laymanUsername, URI, layman, parent=None):
        """Constructor."""
        super(ConnectionManagerDialog, self).__init__(parent)
        app = QtWidgets.QApplication.instance()   
        self.setObjectName("ConnectionManagerDialog")  
        proxy_style = ProxyStyle(app.style())        
        self.setStyle(proxy_style)
        self.setupUi(self)
        self.utils = utils
        self.server = server
        self.laymanUsername = laymanUsername
        self.URI = URI
        self.layman = layman
        self.setUi()
        
    def setUi(self):
        if self.server or self.layman.current != None:
            self.server = True
            proj = QgsProject.instance()
            self.server, type_conversion_ok = proj.readEntry("Layman", "Server","")
            name, type_conversion_ok = proj.readEntry("Layman", "Name","")            
        self.utils.recalculateDPI()        
        self.pushButton_Connect.setEnabled(False)      
        path = self.layman.plugin_dir + os.sep + "server_list.txt"
        servers = self.utils.csvToArray(path)
      
        for i in range (0,len(servers)):

            if not self.server:
                if i == len(servers) - 1: ## vyjimka pro alias na test server bude ostraneno
                    self.comboBox_server.addItem("test HUB")
                else:                 
                    if len(servers[i]) == 6:
                        self.comboBox_server.addItem(servers[i][5])  
                    else:
                       self.comboBox_server.addItem(servers[i][0].replace("www.", "").replace("https://", ""))
            else:         
                if not self.layman.loggedThrowProject:
                    if self.server == servers[i][1] and self.server != "http://157.230.109.174/client":
                        self.comboBox_server.addItem(self.server.replace("/client",""))
                        self.layman.setServers(servers, i) 
                        print("loaded name is "+name)
                        self.pushButton_Connect.clicked.connect(lambda: self.layman.openAuthLiferayUrl2(name))
                        break
                    elif self.server == "http://157.230.109.174/client" and servers[i][1] == self.server:
                        self.comboBox_server.addItem("test HUB")                  
                        self.layman.setServers(servers, i)
                        print("loaded name is "+name)
                        self.pushButton_Connect.clicked.connect(lambda: self.layman.openAuthLiferayUrl2(name))
                        break
                else:      
                    if len(servers[i]) == 6:
                        self.comboBox_server.addItem(servers[i][5])  
                    else:
                       self.comboBox_server.addItem(servers[i][0].replace("www.", "").replace("https://", ""))             
  
                       
        if self.laymanUsername == "":
            if not self.server:
                self.layman.setServers(servers, 0) ## nastavujeme prvni server

        self.comboBox_server.currentIndexChanged.connect(lambda: self.layman.setServers(servers, self.comboBox_server.currentIndex()))
        if (os.path.isfile(os.getenv("HOME") + os.sep + ".layman" + os.sep +'layman_user.INI')):
            config = self.utils.loadIni()   
            if 'login' in config['DEFAULT']:
                if len(config['DEFAULT']['login']) > 0:
                    #self.layman.Agrimail = config['DEFAULT']['login']
                    self.pushButton_Connect.setEnabled(True)  
                # self.lineEdit_userName.setText(config['DEFAULT']['login'])

            for i in range (0, self.comboBox_server.count()):   
                if not self.server:
                    if self.layman.authCfg == "a67e5fd":
                        self.comboBox_server.setCurrentIndex(len(servers) - 1)
                    else:
                        if "server" in config['DEFAULT']:
                            if(self.comboBox_server.itemText(i) == config['DEFAULT']['server'].replace("www.", "").replace("https://", "")):
                                self.comboBox_server.setCurrentIndex(i)
        else:
            try:
                os.makedirs(os.getenv("HOME") + os.sep + ".layman")
            except:
                print("layman directory already exists")       
            self.pushButton_Connect.setEnabled(True)
        # self.lineEdit_userName.textChanged.connect(self.checkUsername)
        self.pushButton_close.clicked.connect(lambda: self.close())
        if QgsSettings().value("laymanLastServer") != None:
            self.comboBox_server.setCurrentIndex(int(QgsSettings().value("laymanLastServer")))
        if not self.server:
            self.pushButton_Connect.clicked.connect(lambda: self.layman.openAuthLiferayUrl2())     
        self.pushButton_NoLogin.clicked.connect(lambda: self.withoutLogin(servers, self.comboBox_server.currentIndex()))
        self.pushButton_Continue.setEnabled(False)
        registerSuffix = "/home?p_p_id=com_liferay_login_web_portlet_LoginPortlet&p_p_lifecycle=0&p_p_state=maximized&p_p_mode=view&saveLastPath=false&_com_liferay_login_web_portlet_LoginPortlet_mvcRenderCommandName=%2Flogin%2Fcreate_account"
        self.comboBox_server.currentTextChanged.connect(self.setReg)
        self.label_sign.setOpenExternalLinks(True)
        if self.layman.locale == "cs":
            self.label_sign.setText('<a href="https://'+self.comboBox_server.currentText().replace('https://','').replace('home','')+registerSuffix+'">Registrovat</a>')
        else:
            self.label_sign.setText('<a href="https://'+self.comboBox_server.currentText().replace('https://','').replace('home','')+registerSuffix+'">Register</a>')         
        self.setStyleSheet("#DialogBase {background: #f0f0f0 ;}")        
        self.pushButton_logout.clicked.connect(lambda: self.logout())
        
        if self.laymanUsername != "":
            self.pushButton_logout.setEnabled(True)
            self.pushButton_NoLogin.setEnabled(False)
            self.pushButton_Connect.setEnabled(False)
            self.comboBox_server.setEnabled(False)
            # self.lineEdit_userName.setEnabled(False)
            if self.layman.locale == "cs":
                self.setWindowTitle("Layman - Přihlášený uživatel: " + self.laymanUsername)
            else:
                self.setWindowTitle("Layman - Logged user: " + self.laymanUsername)

        else:
            self.pushButton_logout.setEnabled(False)
            self.pushButton_NoLogin.setEnabled(True)
            self.pushButton_Connect.setEnabled(True)
            self.comboBox_server.setEnabled(True)
            # self.lineEdit_userName.setEnabled(True)
        self.utils.setAuthCfg(self.layman.authCfg)    
        self.show()    
    def checkUsername(self, name):
        n = name.split("@")
        if(len(n[0]) > 0):
            self.pushButton_Connect.setEnabled(True)        
            self.layman.Agrimail = name
        else:
            self.pushButton_Connect.setEnabled(False)
    def setReg(self):
        registerSuffix = "/home?p_p_id=com_liferay_login_web_portlet_LoginPortlet&p_p_lifecycle=0&p_p_state=maximized&p_p_mode=view&saveLastPath=false&_com_liferay_login_web_portlet_LoginPortlet_mvcRenderCommandName=%2Flogin%2Fcreate_account"
        if self.layman.locale == "cs":
            self.label_sign.setText('<a href="https://'+self.comboBox_server.currentText().replace('https://','').replace('home','')+registerSuffix+'">Registrovat</a>')
        else:
            self.label_sign.setText('<a href="https://'+self.comboBox_server.currentText().replace('https://','').replace('home','')+registerSuffix+'">Register</a>')            
    def refreshAfterFailedLogin(self):
        self.pushButton_Connect.setEnabled(True)        
    def logout(self):
        self.layman.loggedThrowProject = False
        self.layman.disableEnvironment()      
        self.layman.current = None  
        self.layman.qfieldReady = False 
        self.layman.laymanUsername = ""  
        self.layman.textbox.setText("Layman")
        self.close() 
        self.pushButton_NoLogin.setEnabled(True)
        self.pushButton_Connect.setEnabled(True)

        try:
            QgsProject.instance().crsChanged.disconnect()
        except:
            print("crs changed not connected")
        self.layman.menu_UserInfoDialog.setEnabled(True)
        self.layman.laymanUsername = ""
        self.layman.isAuthorized = False        
        self.layman.current = None
        self.layman.server = None     
        self.layman.compositeList = []   
        self.layman.URI = None     
        self.layman.instance = None   
    def withoutLogin(self, servers, i):
        self.layman.menu_CurrentCompositionDialog.setEnabled(False)
        self.layman.isAuthorized = False
        self.layman.URI = servers[i][1]
        self.utils.URI = servers[i][1]
        self.layman.menu_AddLayerDialog.setEnabled(True)    
        self.layman.laymanUsername = "browser"
        self.pushButton_logout.setEnabled(True)
        self.pushButton_NoLogin.setEnabled(False)
        self.pushButton_Connect.setEnabled(False)
        self.layman.menu_UserInfoDialog.setEnabled(True)
        self.layman.menu_AddMapDialog.setEnabled(True)
        self.layman.instance = None
        threading.Thread(target=lambda: self.layman.fillCompositionDict()).start()
        self.close()           