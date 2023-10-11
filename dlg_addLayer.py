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
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton, QMessageBox
from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidgetItemIterator
from PyQt5.QtGui import QPixmap
from qgis.core import *
import threading
import requests
import pandas as pd
from PyQt5.QtWidgets import QPushButton
from PyQt5 import uic
import tempfile
import asyncio



# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dlg_addLayer.ui'))


class AddLayerDialog(QtWidgets.QDialog, FORM_CLASS):

    enableWfsButton = pyqtSignal(bool, QPushButton)
    getLayers = pyqtSignal(bool)
    postgisFound = pyqtSignal(bool)
    layerDeletedSuccessfully = pyqtSignal()
    permissionInfo = pyqtSignal(bool,list, int)
    progressDone = pyqtSignal()
    
    
    def __init__(self, utils, isAuthorized, laymanUsername, URI, layman, parent=None):
        """Constructor."""
        super(AddLayerDialog, self).__init__(parent)
        self.setObjectName("AddLayerDialog")
        self.utils = utils
        self.isAuthorized = isAuthorized
        self.laymanUsername = laymanUsername
        self.URI = URI
        self.layman = layman
        self.setupUi(self)
        self.setUi()



    def connectEvents(self):
        self.enableWfsButton.connect(self.onWfsButton)
        self.getLayers.connect(self.loadLayersThread)
        self.postgisFound.connect(self.on_postgis_found)
        QgsApplication.messageLog().messageReceived.connect(self.write_log_message)
        self.layerDeletedSuccessfully.connect(self._onLayerDeletedSuccessfully)
        self.permissionInfo.connect(self.afterPermissionDone)
        self.progressDone.connect(self._onProgressDone)


    
    def setPermissionsWidget(self, option):        
        self.page1.setVisible(option)
        self.page2.setVisible(not option)
        self.page1.setFixedHeight(700) 
        if option == True:
            names = list()
            for i in range (0, len(self.treeWidget.selectedItems())):
                names.append(self.treeWidget.selectedItems()[i].text(0))
            self.setPermissionsUI(names)

    def setUi(self):
        self.pushButton_setPermissions.clicked.connect(lambda: self.setPermissionsWidget(True))
        self.pushButton_back.clicked.connect(lambda: self.setPermissionsWidget(False))
        self.permissionsConnected = False
        self.connectEvents()
        self.utils.recalculateDPI()
        self.pushButton_layerRedirect.hide()
        self.pushButton_layerRedirect.setEnabled(False)
        self.pushButton_urlWfs.setEnabled(False)
        self.pushButton_urlWms.setEnabled(False)
        self.pushButton.setEnabled(False)
        self.pushButton_wfs.setEnabled(False)
        self.pushButton_delete.setEnabled(False)
        self.pushButton_setPermissions.setEnabled(False)
        self.label_noUser.hide()        
        self.pushButton_postgis.setEnabled(False)        
        try:
            checked = self.utils.getConfigItem("layercheckbox")
        except:
            checked = False
        if checked == "0":
            self.checkBox_own.setCheckState(0)
            checked = False
        if checked == "1":
            self.checkBox_own.setCheckState(2)
            checked = True

        self.pushButton_delete.clicked.connect(lambda: self.callDeleteLayer(self.treeWidget.selectedItems(), self.layerNamesDict))
        self.pushButton_layerRedirect.clicked.connect(lambda: self.layerInfoRedirect(self.treeWidget.selectedItems()[0].text(0)))
        self.pushButton.clicked.connect(lambda: self.readLayerJson(self.treeWidget.selectedItems(), "WMS"))
        self.pushButton_wfs.clicked.connect(lambda: self.readLayerJson(self.treeWidget.selectedItems(), "WFS"))
        self.pushButton_postgis.clicked.connect(lambda: self.loadPostgisLayer(self.treeWidget.selectedItems()[0]))
        self.pushButton_urlWms.clicked.connect(lambda: self.copyLayerUrl(self.treeWidget.selectedItems()[0].text(0),self.treeWidget.selectedItems()[0].text(1),"wms"))
        self.pushButton_urlWfs.clicked.connect(lambda: self.copyLayerUrl(self.treeWidget.selectedItems()[0].text(0),self.treeWidget.selectedItems()[0].text(1),"wfs"))
        if not self.isAuthorized:
            self.label_noUser.show()
            self.checkBox_own.setEnabled(False)
        self.treeWidget.itemClicked.connect(self.enableDeleteButton)
        self.treeWidget.itemSelectionChanged.connect(self.checkSelectedCount)
        self.treeWidget.itemClicked.connect(self.setPermissionsButton)
        self.treeWidget.itemClicked.connect(lambda: threading.Thread(target=lambda: self.showThumbnail2(self.treeWidget.selectedItems()[0])).start())
        self.treeWidget.itemClicked.connect(lambda: threading.Thread(target=lambda: self.checkIfPostgis(self.treeWidget.selectedItems()[0])).start())
        self.filter.valueChanged.connect(self.filterResults)
        self.treeWidget.setColumnWidth(0, 250)
        self.treeWidget.setColumnWidth(2, 80)
        self.pushButton_close.clicked.connect(lambda: self.close())
        self.checkBox_own.stateChanged.connect(self.rememberValueLayer)
        self.setStyleSheet("#DialogBase {background: #f0f0f0 ;}")       
        self.progressBar_loader.show()
        asyncio.run(self.loadLayersThread(checked))
        self.checkBox_own.stateChanged.connect(self.loadLayersThread)
        if self.isAuthorized:
            self.checkBox_own.setEnabled(True)
        else:
            self.checkBox_own.setEnabled(False)

        self.label_loading.show()       
        self.show()
        result = self.exec_()



    def setPermissionsUI(self, layerName): 
        self.listWidget_read.clear()
        self.listWidget_write.clear()
        self.comboBox_users.clear()
        
        
        self.info = 0
        self.pushButton_close.clicked.connect(lambda: self.close())       
        self.listWidget_read.itemSelectionChanged.connect(lambda: self.checkPermissionButtons())
        self.listWidget_write.itemSelectionChanged.connect(lambda: self.checkPermissionButtons())
        self.pushButton_removeRead.setEnabled(False)
        self.pushButton_removeWrite.setEnabled(False)
        ## combobox full text part
        self.comboBox_users.setEditable(True)
        self.comboBox_users.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.comboBox_users.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            ##

        uri = self.URI + "/rest/users"
        usersDict = dict()
        if self.layman.locale == "cs":
            usersDict['EVERYONE'] = 'VŠICHNI'
        else:
            usersDict['EVERYONE'] = 'EVERYONE'
        usersDictReversed = dict()
        if self.layman.locale == "cs":
            usersDictReversed['EVERYONE'] = 'VŠICHNI'
        else:
            usersDictReversed['EVERYONE'] = 'EVERYONE'   
        r = self.utils.requestWrapper("GET", uri, payload = None, files = None)
        res = self.utils.fromByteToJson(r.content)
        userCount = len(res)   
        if self.layman.locale == "cs":
            self.comboBox_users.addItem('VŠICHNI')
        else:
            self.comboBox_users.addItem('EVERYONE')
        for i in range (0, userCount):
            usersDict[res[i]['name'] if res[i]['name'] !="" else res[i]['username']] = res[i]['username']
            usersDictReversed[res[i]['username']] = res[i]['name'] if res[i]['name'] !="" else res[i]['username']
            if (res[i]['name'] != self.laymanUsername):                
                self.comboBox_users.addItem(res[i]['name'] if res[i]['name'] !="" else res[i]['username'])

        if (len(layerName) == 1):
            layerName[0] = self.layerNamesDict[layerName[0]]
            uri = self.URI + "/rest/"+self.laymanUsername+"/layers/"+layerName[0]
            r = self.utils.requestWrapper("GET", uri, payload = None, files = None)
            res = self.utils.fromByteToJson(r.content)
            lenRead = len(res['access_rights']['read'])
            lenWrite = len(res['access_rights']['write'])
            for i in range (0, lenRead):
                self.listWidget_read.addItem(usersDictReversed[res['access_rights']['read'][i]])
            for i in range (0, lenWrite):
                self.listWidget_write.addItem(usersDictReversed[res['access_rights']['write'][i]])
        else:
            name = self.utils.getUserFullName()
            self.listWidget_read.addItem(name)
            self.listWidget_write.addItem(name)          
        if not self.permissionsConnected:            
            self.pushButton_save.clicked.connect(lambda:  self.progressBar_loader.show())
            self.pushButton_save.clicked.connect(lambda: self.askForMapPermissionChanges(layerName, usersDict, "layers"))          
            self.pushButton_addRead.clicked.connect(lambda:  self.checkAddedItemDuplicity("read"))
            self.pushButton_addWrite.clicked.connect(lambda: self.setWritePermissionList())
            self.pushButton_removeRead.clicked.connect(lambda: self.removeReadPermissionList(usersDictReversed))
            self.pushButton_removeWrite.clicked.connect(lambda: self.removeWritePermissionList(usersDictReversed))
            self.permissionsConnected = True      
  

    def callDeleteLayer(self, layers, layerNames):
        items = list()
        for i in range (0, len(layers)):
            items.append(layers[i].text(0))
        question = True
        if len(items) > 1:
            if self.layman.locale == "cs":
                msgbox = QMessageBox(QMessageBox.Question, "Delete layer", "Chcete opravdu smazat vybrané vrstvy?")
            else:
                msgbox = QMessageBox(QMessageBox.Question, "Delete layer", "Do you want delete selected layers?")
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            reply = msgbox.exec()
            if (reply == QMessageBox.Yes):
                question = False
        for j in range (0, len(items)):
            self.layerDelete(items[j], layerNames, question)
    def layerDelete(self, name,layerNames, question = True):
        title = name
        name = layerNames[title]
        if question:
            if self.layman.locale == "cs":
                msgbox = QMessageBox(QMessageBox.Question, "Delete layer", "Chcete opravdu smazat vrstvu "+str(name)+"?")
            else:
                msgbox = QMessageBox(QMessageBox.Question, "Delete layer", "Do you want delete layer "+str(name)+"?")
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            reply = msgbox.exec()
        else:
            reply = QMessageBox.Yes
        if (reply == QMessageBox.Yes):     
            name = self.utils.removeUnacceptableChars(name).lower()
            self.progressBar_loader.show()
            threading.Thread(target=lambda: self.layerDeleteThread(name)).start()          


    def layerInfoRedirect(self, name):
        url = self.URI+'/rest/'+self.laymanUsername+"/layers/" + name
        response = self.utils.requestWrapper("GET", url, payload = None, files = None)
        r = self.utils.fromByteToJson(response.content)
        try:
            url = r['metadata']['record_url']
            webbrowser.open(url, new=2) ## redirect na micku pro více info
        except:
            self.utils.emitMessageBox.emit(["Odkaz není k dispozici.", "Link is unavailable."])


    def copyLayerUrl(self, name, workspace, service):
        url = self.URI+'/rest/'+workspace+'/layers/'+self.utils.removeUnacceptableChars(name)
        response = self.utils.requestWrapper("GET", url, payload = None, files = None)
        res = self.utils.fromByteToJson(response.content)
        if res == None:
            return
        try:
            df=pd.DataFrame([res[service]['url']])
            df.to_clipboard(index=False,header=False)
            self.utils.showMessageBar([" URL uloženo do schránky."," URL saved to clipboard."],Qgis.Success)
        except:
            self.utils.showMessageBar([" URL nebylo uloženo do schránky."," URL was not saved to clipboard."],Qgis.Warning)

    def showThumbnail2(self, it):
        layer = it.text(0) 
        workspace = it.text(1)
        if self.checkBox_thumbnail.checkState() == 0:

            layer = self.layerNamesDict[layer]
            url = self.URI+'/rest/' +workspace+'/layers/'+layer+'/thumbnail'

            r = requests.get(url, headers = self.utils.getAuthHeader(self.utils.authCfg))
            data = r.content
            pixmap = QPixmap(200, 200)
            pixmap.loadFromData(data)
            smaller_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.FastTransformation)
            self.label_thumbnail.setPixmap(smaller_pixmap)
            self.label_thumbnail.setAlignment(Qt.AlignCenter)

    def checkIfPostgis(self, it):
        layer = self.utils.removeUnacceptableChars(it.text(0))
        workspace = it.text(1)
        url = self.URI+'/rest/'+workspace+'/layers/'+str(layer).lower()      
        r = requests.get(url, headers = self.utils.getAuthHeader(self.utils.authCfg))
        if "db" in r.json():
            if "external_uri" in r.json()["db"]:
                self.postgisFound.emit(True)
            else:
                self.postgisFound.emit(False)
        else:
            self.postgisFound.emit(False)
    def filterResults(self, value):

        iterator = QTreeWidgetItemIterator(self.treeWidget, QTreeWidgetItemIterator.All)
        while iterator.value():
            item = iterator.value()
            if value.lower() not in item.text(0).lower():
                item.setHidden(True)
            else:
                item.setHidden(False)
            iterator +=1

    def rememberValueLayer(self, value):    
        if value == 2:
            self.utils.appendIniItem("layerCheckbox", "1")
        if value == 0:
            self.utils.appendIniItem("layerCheckbox", "0")

    async def loadLayersThread(self, onlyOwn=False):
        self.layerNamesDict = dict()
        self.treeWidget.clear()
        if self.laymanUsername and self.isAuthorized:
            url = self.URI+'/rest/'+self.laymanUsername+'/layers'
            #r = self.utils.requestWrapper("GET", url, payload = None, files = None)
            r = await (self.utils.asyncRequestWrapper("GET", url))
            data = self.utils.fromByteToJson(r) 
            if onlyOwn:
                for row in range(0, len(data)):
                    if "native_crs" in data[row] and 'wfs_wms_status' in data[row]:
                        item = QTreeWidgetItem([data[row]['title'],data[row]['workspace'],"own",data[row]['native_crs'],data[row]['wfs_wms_status']])
                    else:
                        item = QTreeWidgetItem([data[row]['title'],data[row]['workspace'],"own"])
                    self.treeWidget.addTopLevelItem(item)
                    self.layerNamesDict[data[row]['title']] = data[row]['name']

                QgsMessageLog.logMessage("layersLoaded")
            else:
                url = self.URI+'/rest/layers'
                #r = self.utils.requestWrapper("GET", url, payload = None, files = None)
                r = await (self.utils.asyncRequestWrapper("GET", url))
                dataAll = self.utils.fromByteToJson(r)
                permissions = ""
                for row in range(0, len(dataAll)):
                    if self.laymanUsername in dataAll[row]['access_rights']['read'] or "EVERYONE" in dataAll[row]['access_rights']['read']:
                        permissions = "read"
                    if self.laymanUsername in dataAll[row]['access_rights']['write'] or "EVERYONE" in dataAll[row]['access_rights']['write']:
                        permissions = "write"
                    if dataAll[row] in data:
                        permissions = "own"
                    if permissions != "":
                        if "native_crs" in dataAll[row]  and 'wfs_wms_status' in dataAll[row]:
                            item = QTreeWidgetItem([dataAll[row]['title'],dataAll[row]['workspace'],permissions,dataAll[row]['native_crs'],dataAll[row]['wfs_wms_status']])
                        else:
                            item = QTreeWidgetItem([dataAll[row]['title'],dataAll[row]['workspace'],permissions])

                        self.layerNamesDict[dataAll[row]['title']] = dataAll[row]['name']
                        self.treeWidget.addTopLevelItem(item)

                QgsMessageLog.logMessage("layersLoaded")
        else:
            url = self.URI+'/rest/layers'
            #r = self.utils.requestWrapper("GET", url, payload = None, files = None)
            r = await (self.utils.asyncRequestWrapper("GET", url))
            data = self.utils.fromByteToJson(r)
            for row in range(0, len(data)):
                if "EVERYONE" in data[row]['access_rights']['read']:
                    permissions = "read"
                if "EVERYONE" in data[row]['access_rights']['write']:
                    permissions = "write"
                if "native_crs" in data[row]  and 'wfs_wms_status' in data[row]:
                    item = QTreeWidgetItem([data[row]['title'],data[row]['workspace'],permissions,data[row]['native_crs'],data[row]['wfs_wms_status']])
                else:
                    item = QTreeWidgetItem([data[row]['title'],data[row]['workspace'],permissions])
                self.layerNamesDict[data[row]['title']] = data[row]['name']
                self.treeWidget.addTopLevelItem(item)
            QgsMessageLog.logMessage("layersLoaded")
        self.progressBar_loader.hide()
   
    def enableDeleteButton(self, item, col):
        self.pushButton.setEnabled(True)
        self.pushButton_urlWfs.setEnabled(True)
        self.pushButton_urlWms.setEnabled(True)
        self.pushButton_layerRedirect.setEnabled(True)  
        self.checkSelectedCount()
        self.checkServiceButtons()

    def checkServiceButtons(self):
        if self.objectName() == "AddLayerDialog":
            if self.checkFileType(self.treeWidget.selectedItems()[0].text(0),self.treeWidget.selectedItems()[0].text(1)) == "vector":
                if self.objectName() == "AddLayerDialog":
                    print(self.pushButton_wfs.setEnabled(True))
                    self.enableWfsButton.emit(True, self.pushButton_wfs)
            elif self.checkFileType(self.treeWidget.selectedItems()[0].text(0),self.treeWidget.selectedItems()[0].text(1)) == "raster":
                if self.objectName() == "AddLayerDialog":
                    self.enableWfsButton.emit(False, self.pushButton_wfs)
            else:
                if self.objectName() == "AddLayerDialog":
                    self.enableWfsButton.emit(True, self.pushButton_wfs)

    def onWfsButton(self, enable, button):
        try:
            button.setEnabled(enable)
        except:
            pass
    def checkSelectedCount(self):
        if (len(self.treeWidget.selectedItems()) > 1):
            self.pushButton_setPermissions.setEnabled(True)
            self.pushButton_delete.setEnabled(True)
            self.pushButton.setEnabled(True)
            self.checkBox_thumbnail.setCheckState(2)
        else:
            self.pushButton_setPermissions.setEnabled(True)
            self.pushButton_delete.setEnabled(True)
            self.pushButton.setEnabled(True)
    def setPermissionsButton(self, item):
        if item.text(2) != "own":
            self.pushButton_setPermissions.setEnabled(False)
            self.pushButton_delete.setEnabled(False)
        else:
            self.pushButton_setPermissions.setEnabled(True)
            self.pushButton_delete.setEnabled(True)

    def checkFileType(self, name, workspace):
        name = self.layerNamesDict[name]
        url = self.URI+'/rest/'+workspace+'/layers/'+self.utils.removeUnacceptableChars(name)
        response = self.utils.requestWrapper("GET", url, payload = None, files = None)
        res = self.utils.fromByteToJson(response.content)
        if "file" in res:
            return res['file']['file_type']
        else:
            return ""

    def on_postgis_found(self, found):
        if self.objectName() == "AddLayerDialog":
            if found:
                self.pushButton_postgis.setEnabled(True)
            else:
                self.pushButton_postgis.setEnabled(False)

    def readLayerJson(self,layerName, service):
        self.progressBar_loader.show()
        for i in range (0, len(self.treeWidget.selectedItems())):
            name = self.treeWidget.selectedItems()[i].text(0)
            workspace = self.treeWidget.selectedItems()[i].text(1)
            self.selectedWorkspace = workspace
            threading.Thread(target=lambda: self.readLayerJsonThread(name,service, workspace)).start()

    def readLayerJsonThread(self, layerName,service, workspace):
        layerNameTitle =layerName
        layerName = self.layerNamesDict[layerName]   
        if self.utils.checkLayerOnLayman(layerName, self.selectedWorkspace, self.laymanUsername):
            layerName = self.utils.removeUnacceptableChars(layerName)
            url = self.URI+'/rest/'+workspace+'/layers/'+layerName
            r = self.utils.requestWrapper("GET", url, payload = None, files = None)
            try:
                data = r.json()
            except:
                self.utils.showErr.emit(["Vrstva není k dispozici!", "Layer is not available!"], "code: " + str(r.status_code), str(r.content), Qgis.Warning, url)
                return
            if (service == "WMS"):
                try:
                    wmsUrl = data['wms']['url']
                except:
                    self.utils.showErr.emit(["Vrstva není k dispozici!", "Layer is not available!"], "code: " + str(r.status_code), str(r.content), Qgis.Warning, url)
                    return
                format = 'png'
                epsg = 'EPSG:5514'
                everyone = False
                if 'EVERYONE' in data['access_rights']['read']:
                    everyone = True
                timeDimension = {}
                if 'time' in data['wms']:
                    timeDimension = data['wms']

                groupName=""
                subgroup=""
                visibility = ''
                success = self.utils.loadWms(wmsUrl, layerName,layerNameTitle, format, epsg, workspace, groupName,subgroup, timeDimension,visibility, everyone)
                if not success:
                    self.utils.emitMessageBox.emit(["Vrstva: "+layerName + " je poškozena a nebude načtena.", "Layer: "+layerName + " is corrupted and will not be loaded."])
                 
            if (service == "WFS"):
                try:
                    wfsUrl = data['wfs']['url']
                except:
                    self.showErr.emit(["Vrstva není k dispozici!", "Layer is not available!"], "code: " + str(r.status_code), str(r.content), Qgis.Warning, url)
                    return
                print("loading WFS")
                success = self.utils.loadWfs(wfsUrl, layerName, layerNameTitle, workspace)
                if not success:
                    self.utils.emitMessageBox.emit(["Vrstva: "+layerName + " je poškozena a nebude načtena.", "Layer: "+layerName + " is corrupted and will not be loaded."])
                   
            QgsMessageLog.logMessage("layersLoaded")
        else:
            self.utils.emitMessageBox.emit(["Vrstva "+layerName+ " nelze nahrát","Something went wrong with layer: " + layerName])
            QgsMessageLog.logMessage("layersLoaded")
    def write_log_message(self,message, tag, level):
        if message == "layersLoaded":            
            try:
                self.progressBar_loader.hide()
            except:
                pass
    def layerDeleteThread(self, name):
        url = self.URI+'/rest/'+self.laymanUsername+'/layers/'+name
        response = self.utils.requestWrapper("DELETE", url, payload = None, files = None)
        try:
            checked = self.utils.getConfigItem("layercheckbox")
        except:
            checked = False
        if checked == "0":
            checked = False
        if checked == "1":
            checked = True      
        self.getLayers.emit(checked)

        if response.status_code == 200:        
            self.layerDeletedSuccessfully.emit()
        else:
            self.utils.showErr.emit(["Vrstva nebyla smazána!", "Layer was not deleted!"], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)
    def _onLayerDeletedSuccessfully(self):   
        if self.objectName() == "AddLayerDialog":
            self.pushButton_postgis.setEnabled(False)
            self.pushButton_wfs.setEnabled(False)
            self.pushButton.setEnabled(False)
            self.pushButton_setPermissions.setEnabled(False)
            self.pushButton_delete.setEnabled(False)
            self.pushButton_urlWms.setEnabled(False)
            self.pushButton_urlWfs.setEnabled(False)
            self.progressBar_loader.hide()
            self.label_thumbnail.setText(' ')
    def checkAddedItemDuplicity(self, type):
        itemsTextListRead =  [str(self.listWidget_read.item(i).text()) for i in range(self.listWidget_read.count())]
        itemsTextListWrite =  [str(self.listWidget_write.item(i).text()) for i in range(self.listWidget_write.count())]        
        allItems = [self.comboBox_users.itemText(i) for i in range(self.comboBox_users.count())]      
        if self.comboBox_users.currentText() in allItems:
            if type == "read":
              
                if ((self.comboBox_users.currentText() not in itemsTextListRead)):                  
                    self.listWidget_read.addItem(self.comboBox_users.currentText())
                    return True
                else:
                    self.utils.emitMessageBox.emit(["Tento uživatel se již v seznamu vyskytuje!", "This user already exists in the list!"])         
                    return False
            else:              
                if ((self.comboBox_users.currentText() not in itemsTextListWrite) and type == "write"):               
                    return True
                else:                    
                    self.utils.emitMessageBox.emit(["Tento uživatel se již v seznamu vyskytuje!", "This user already exists in the list!"])              
                    return False
    def setWritePermissionList(self):
        allItems = [self.comboBox_users.itemText(i) for i in range(self.comboBox_users.count())]    
        if self.comboBox_users.currentText() in allItems:
            if self.checkAddedItemDuplicity("write"):
                itemsTextListRead =  [str(self.listWidget_read.item(i).text()) for i in range(self.listWidget_read.count())]
              
                if (self.comboBox_users.currentText() in itemsTextListRead):
                  
                    self.listWidget_write.addItem(self.comboBox_users.currentText())
                    print("1")
                else:            
                    self.listWidget_write.addItem(self.comboBox_users.currentText())
                    self.listWidget_read.addItem(self.comboBox_users.currentText())
                    print("2")                
    def checkPermissionButtons(self):
        name = self.utils.getUserName()
        try:
            if self.listWidget_read.currentItem().text() == name:
                self.pushButton_removeRead.setEnabled(False)
            else:
                self.pushButton_removeRead.setEnabled(True)
        except:
            self.pushButton_removeRead.setEnabled(False)
            print("neni vybrana polozka")
        try:
            if self.listWidget_write.currentItem().text() == name:
                self.pushButton_removeWrite.setEnabled(False)
            else:
                self.pushButton_removeWrite.setEnabled(True)
        except:
            self.pushButton_removeWrite.setEnabled(False)
            print("neni vybrana polozka")                    
            
            
    def askForMapPermissionChanges(self,layerName, userDict, type):
        self.failed = list()
        self.statusHelper = True            
        threading.Thread(target=lambda: self.updatePermissions(layerName, userDict, type)).start()
      
            
    def updateAllLayersPermission(self, userDict, layerName, loaded = False):      
        if loaded:
            composition = self.instance.getComposition()
        else:
            url = self.URI + "/rest/"+self.laymanUsername+"/maps/"+layerName[0]+"/file"
            r = self.requestWrapper("GET", url, payload = None, files = None)
            composition = r.json()
        itemsTextListRead =  [str(self.listWidget_read.item(i).text()) for i in range(self.listWidget_read.count())]
        itemsTextListWrite =  [str(self.listWidget_write.item(i).text()) for i in range(self.listWidget_write.count())]
        userNamesRead = list()
        for pom in itemsTextListRead:         
            if pom == "VŠICHNI":
                userNamesRead.append("EVERYONE")          
            else:
                userNamesRead.append(userDict[pom])
        userNamesWrite = list()    
        for pom in itemsTextListWrite:
            if pom == "VŠICHNI":
                userNamesWrite.append("EVERYONE")
            else:
                print(userDict[pom])
                userNamesWrite.append(userDict[pom])
        data = {'access_rights.read': self.utils.listToString(userNamesRead),   'access_rights.write': self.utils.listToString(userNamesWrite)}       
        for layer in composition['layers']:
            name = None
            if (layer['className'] == 'OpenLayers.Layer.Vector'):
                name = layer['protocol']['LAYERS']
            if (layer['className'] == 'HSLayers.Layer.WMS'):
                name = layer['params']['LAYERS']
            if name is not None:
                response = requests.patch(self.URI+'/rest/'+self.laymanUsername+'/layers/'+name, data = data,  headers = self.utils.getAuthHeader(self.authCfg))  
                print(response.content)
                if (response.status_code != 200):        
                    try:
                        if self.utils.fromByteToJson(response.content)["code"] == 15:
                            print("layer not present")
                            return
                    except:
                        pass                                      
                    self.showErr.emit(["Práva nebyla uložena! - " + name,"Permissions was not saved' - "+ name], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)
            else:
                print("there is not possible set permissions for layer")
          
    def updatePermissions(self,layerName, userDict, type, check=False):   
        if len(layerName) == 0:
            if not self.utils.checkPublicationStatus(layerName[0]):
               self.utils.showQgisBar(["Tato vrstva je stále v publikaci. V tuto chvíli není možné aktualizovat práva","This layer is still in publication. It is not possible to update permissions at this time."], Qgis.Warning)   
               self.progressDone.emit()
               return
        itemsTextListRead =  [str(self.listWidget_read.item(i).text()) for i in range(self.listWidget_read.count())]
        itemsTextListWrite =  [str(self.listWidget_write.item(i).text()) for i in range(self.listWidget_write.count())]
        userNamesRead = list()  
        # print(itemsTextListRead)
        for pom in itemsTextListRead:         
            if pom == "VŠICHNI":            
                userNamesRead.append("EVERYONE")          
            else:
                print(pom)
                if "," in pom:
                    pom = pom.split(", ")[1]     
                print(userDict)                                               
                userNamesRead.append(userDict[pom])
        userNamesWrite = list()      
        for pom in itemsTextListWrite:
            if pom == "VŠICHNI":
                userNamesWrite.append("EVERYONE")
            else:
                if "," in pom:
                    pom = pom.split(", ")[1]
                userNamesWrite.append(userDict[pom])
        data = {'access_rights.read': self.utils.listToString(userNamesRead),   'access_rights.write': self.utils.listToString(userNamesWrite)}    
        for layer in layerName:
            layer = self.utils.removeUnacceptableChars(layer)      
            url = self.URI+'/rest/'+self.laymanUsername+'/'+type+'/'+layer
            response = requests.patch(url, data = data,  headers = self.utils.getAuthHeader(self.utils.authCfg))             
            if (response.status_code != 200):
                self.failed.append(layer)         
                self.utils.showErr.emit(["Práva nebyla uložena! - " + layer,"Permissions was not saved' - "+ layer], "code: " + str(response.status_code), str(response.content), Qgis.Warning, url)
                (list,str,str,Qgis.MessageLevel, str)  
                self.statusHelper = False 
         
        if (self.statusHelper and self.info == 0):
            print(self.failed)
            self.permissionInfo.emit(True, self.failed, 0)                
        else:
            self.permissionInfo.emit(False, self.failed, 0)                
                
    def afterPermissionDone(self, success, failed, info):
        if self.objectName() == "AddLayerDialog":
            self.progressBar_loader.hide()             
            if success:
                self.utils.emitMessageBox.emit(["Práva byla úspěšně uložena.", "Permissions was saved successfully."])                           
            else:
                self.utils.emitMessageBox.emit(["Práva nebyla uložena pro vrstvu: " + str(failed).replace("[","").replace("]",""), "Permissions was not saved for layer: " + str(failed).replace("[","").replace("]","")])                           
                    
    def removeReadPermissionList(self, usersDictReversed):       
        if usersDictReversed[self.laymanUsername] == self.listWidget_read.currentItem().text() or usersDictReversed[self.laymanUsername] == self.listWidget_write.currentRow():
            self.utils.showQgisBar(["Není možné odebrat aktuálního uživatele.","Unable to remove current user."], Qgis.Warning)
            return
        self.deleteItem(self.listWidget_read.currentItem().text())
        self.listWidget_read.removeItemWidget(self.listWidget_read.takeItem(self.listWidget_read.currentRow()))
    def removeWritePermissionList(self, usersDictReversed):
        if usersDictReversed[self.laymanUsername] == self.listWidget_write.currentItem().text():
            self.utils.showQgisBar(["Není možné odebrat aktuálního uživatele.","Unable to remove current user."], Qgis.Warning)
            return        
        self.listWidget_write.removeItemWidget(self.listWidget_write.takeItem(self.listWidget_write.currentRow()))
    def deleteItem(self, itemName):
        items_list = self.listWidget_write.findItems(itemName, Qt.MatchExactly)
        for item in items_list:
            r = self.listWidget_write.row(item)
            self.listWidget_write.takeItem(r)       
    def loadPostgisLayer(self, it):
        layerName = self.utils.removeUnacceptableChars(it.text(0))        
        workspace = it.text(1)
        url = self.URI+'/rest/'+workspace+'/layers/'+str(layerName).lower() 
        r = requests.get(url, headers = self.utils.getAuthHeader(self.utils.authCfg))
        data = r.json()
        print(data)
        table = data["db"]["table"]
        schema = data["db"]["schema"]
        geo_column = data["db"]["geo_column"]           
        address = self.utils.find_substring(data["db"]["external_uri"], "@", "/" )
        host = address.split(":")[0]
        port = address.split(":")[1]
        user = self.utils.find_substring(data["db"]["external_uri"], r"://", "@")
        srid = str(4326)
        dbname = data["db"]["external_uri"].split("/")[-1]
        table = '"'+ schema +'"."'+ table + '" (' + geo_column + ') '          
        if ("host.docker.internal" in host):
            host = host.replace("host.docker.internal","localhost") 
        uri = "dbname='"+dbname+"' host="+host+" port="+port+" user='"+user+"' table="+ table +" key='id' srid="+srid
        style = self.layman.getStyle(layerName, None, workspace)
        print(style)
        layer = QgsVectorLayer(uri, it.text(0), 'postgres')  
        if not layer.isValid():
            self.utils.showQgisBar(["Vrstva nebyla úspěšně načtena.","Layer was not successfully loaded."], Qgis.Warning)
            print("Layer failed to load!")  
        ## load style 
        if (style[0] == 200):
            if (style[1] == "sld"):
                tempf = tempfile.gettempdir() + os.sep +self.utils.removeUnacceptableChars(layerName)+ ".sld"
                layer.loadSldStyle(tempf)
                   
            if (style[1] == "qml"):
                tempf = tempfile.gettempdir() + os.sep +self.utils.removeUnacceptableChars(layerName)+ ".qml"
                layer.loadNamedStyle(tempf)
        QgsProject.instance().addMapLayer(layer)     
        layer.afterCommitChanges.connect(self.layman.patchPostreLayer)               
    def _onProgressDone(self):
        self.progressBar_loader.hide()         