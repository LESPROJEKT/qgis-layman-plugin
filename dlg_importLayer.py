# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CartoDBDialog
                                 A QGIS plugin
 CartoDB plugin
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
from PyQt5.QtCore import Qt
from qgis.core import *
import tempfile
from .dlg_postgrePass import PostgrePasswordDialog
from .dlg_timeSeries import TimeSeriesDialog
from PyQt5.QtWidgets import (QMessageBox, QTreeWidgetItem, QTreeWidgetItemIterator)
import threading
import re
import json
import PyQt5
from .layman_utils import ProxyStyle

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dlg_importLayer.ui'))


class ImportLayerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self,utils, isAuthorized, laymanUsername, URI, layman, parent=None):
        """Constructor."""
        super(ImportLayerDialog, self).__init__(parent)
        self.utils = utils
        self.isAuthorized = isAuthorized
        self.laymanUsername = laymanUsername
        self.URI = URI
        self.layman = layman
        app = QtWidgets.QApplication.instance()     
        proxy_style = ProxyStyle(app.style())
        self.setStyle(proxy_style)
        self.setupUi(self)
        self.postgis_login = None
        self.postgis_pass = None
        self.setUi()
        
    def connectEvents(self):
        pass
    
    def setStackWidget(self, option): 
        if option == "time":       
            self.page_main.setVisible(False)
            self.page_time.setVisible(True)
            self.page_postgis.setVisible(False)            
            self.showTSDialog()
        if option == "main":       
            self.page_main.setVisible(True)
            self.page_time.setVisible(False)
            self.page_postgis.setVisible(False)      
            self.pushButton.show()
            self.label.show()
            self.comboBox_resampling.show()
        if option == "postgis":       
            self.page_main.setVisible(False)
            self.page_time.setVisible(False)
            self.page_postgis.setVisible(True)                   
      
            
    def setUi(self):
        self.connectEvents()
        self.utils.recalculateDPI()     
        self.label_progress.hide()
        self.pushButton.clicked.connect(lambda: self.callPostRequest(self.treeWidget.selectedItems()))       
        if self.locale == "cs":
            self.label_progress.setText("Úspěšně exportováno: 0 / 0")
        else:
            self.label_progress.setText("Sucessfully exported: 0 / 0")
        self.progressBar.hide()      
        if self.layman.locale == "cs":
            resamplingMethods = ["Není vybrán", "Nejbližší", "Průměr", "rms", "Bilineární", "Gaussovská", "Kubická", "Kubický spline", "Průměr magnitudy a fáze", "Modus"]
        else:            
            resamplingMethods = ["No value", "nearest", "average", "rms", "bilinear", "gauss", "cubic", "cubicspline", "average_magphase", "mode"]
        self.comboBox_resampling.addItems(resamplingMethods)
        self.comboBox_resampling.setEnabled(False)        
        self.label_import.hide()
        self.pushButton.setEnabled(False)      
        self.pushButton_errLog.hide()
        self.pushButton_errLog.clicked.connect(self.copyErrLog)
        self.treeWidget.itemPressed.connect(self.enableButtonImport)      
        self.treeWidget.itemSelectionChanged.connect(lambda: self.disableExport())
        self.treeWidget.itemSelectionChanged.connect(lambda: self.checkIfRasterInSelected())    
        self.treeWidget.setCurrentItem(self.treeWidget.topLevelItem(0),0)
        layers = QgsProject.instance().mapLayers().values()
        mix = list()
        self.initLogFile()
        root = QgsProject.instance().layerTreeRoot()      
        layers = []    
        for child in root.children():
            self.get_layers_in_order(child, layers)
        for layer in layers:
            if (layer.type() == QgsMapLayer.VectorLayer):
                if self.utils.isLayerPostgres(layer):
                    layerType = 'postgres'
                else:
                    layerType = 'vector layer'
            if (layer.type() == QgsMapLayer.RasterLayer):	
                if layer.dataProvider().name() == "arcgismapserver":	
                    layerType = 'arcgis layer'	
                else:	
                    layerType = 'raster layer'
            if layer.providerType() != "wms":
                item = QTreeWidgetItem([layer.name(), layerType])
        
                if (layerType == 'vector layer'):
                    if (layer.name() in self.layman.mixedLayers and layer.name() in mix):
                        pass
                    elif (layer.name() in self.layman.mixedLayers and layer.name() not in mix):
                        self.treeWidget.addTopLevelItem(item)
                        mix.append(layer.name())
                    else:
                        self.treeWidget.addTopLevelItem(item)
                if (layerType == 'raster layer'):
                    self.treeWidget.addTopLevelItem(item)
                if (layerType == 'postgres'):
                    self.treeWidget.addTopLevelItem(item)                      
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("#DialogBase {background: #f0f0f0 ;}")
        self.selectSelectedLayer()
        self.treeWidget.header().resizeSection(0,250)
        self.pushButton_close.clicked.connect(lambda: self.close())  
        self.show()    
        
    def rememberLoginPostgres(self, login, password):
        self.postgis_login = login
        self.postgis_pass = password
                  
    def callPostRequest(self, layers):        
        resamplingMethod = self.comboBox_resampling.currentText()
        if resamplingMethod == "No value":
            resamplingMethod = "Není vybrán"
        def showPostgreDialog(layer):
            self.setStackWidget("postgis")
            self.pushButton.hide()
            self.label.hide()
            self.comboBox_resampling.hide()
            if self.postgis_login is not None and self.postgis_pass is not None:
                self.lineEdit_username.setText(self.postgis_login)
                self.lineEdit_pass.setText(self.postgis_pass)
            self.pushButton_backPostgis.clicked.connect(lambda: self.setStackWidget("main"))
            self.pushButton_pass.clicked.connect(lambda: self.layman.postPostreLayer(layer, self.lineEdit_username.text(), self.lineEdit_pass.text()))
            self.pushButton_pass.clicked.connect(lambda: self.rememberLoginPostgres(self.lineEdit_username.text(), self.lineEdit_pass.text()))            
        self.pushButton_errLog.hide()
        self.ThreadsA = set()
        for thread in threading.enumerate():
            self.ThreadsA.add(thread.name)
        self.layman.uploaded = 0
        self.layman.batchLength = len(layers)        
        if self.checkIfAllLayerAreRaster(layers):
            if self.locale == "cs":
                msgbox = QMessageBox(QMessageBox.Question, "Layman", "Je vybráno více rastrových vrstev. Chcete je exportovat jako časové? Symbologie bude přebrána z prvního rastru.")
            else:
                msgbox = QMessageBox(QMessageBox.Question, "Layman", "Multiple raster layers are selected. Do you want to export them as time series? The symbology will be taken from the first raster.")
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            reply = msgbox.exec()
            if (reply == QMessageBox.Yes):
                
                self.setStackWidget("time")
                return
        self.label_progress.show()        
        if self.locale == "cs":
            self.label_progress.setText("Úspěšně exportováno: 0 / " + str(len(layers)) )
        else:
            self.label_progress.setText("Sucessfully exported 0 / " + str(len(layers)) )        
        self.layersToUpload = len(layers)
        bulk = False
        if self.layersToUpload > 1:
            for item in layers:
                if (self.checkExistingLayer(item.text(0))):
                    if self.locale == "cs":
                        msgbox = QMessageBox(QMessageBox.Question, "Layman", "Je vybráno více vrstev a některé z nich již na serveru existují. Chcete je hromadně přepsat?")
                    else:
                        msgbox = QMessageBox(QMessageBox.Question, "Layman", "Multiple layers are selected and some of them already exist on the server. Do you want to overwrite them?")
                    msgbox.addButton(QMessageBox.Yes)
                    msgbox.addButton(QMessageBox.No)
                    msgbox.setDefaultButton(QMessageBox.No)
                    reply = msgbox.exec()
                    if (reply == QMessageBox.Yes):  
                        bulk = True     
                        break  
                    else:
                        return              
        for item in layers:
            layer = QgsProject.instance().mapLayersByName(item.text(0))[0]
            if self.utils.isLayerPostgres(layer):
                showPostgreDialog(layer)                
            else:                
                if not bulk:   
                    self.layman.postRequest(item.text(0), False, True, False, resamplingMethod)
                else:
                    self.layman.postRequest(item.text(0), False, True, True, resamplingMethod)
    def checkIfAllLayerAreRaster(self, layers): 
        if len(layers) == 1:
            return False
        for item in layers:
            layer = QgsProject.instance().mapLayersByName(item.text(0))[0]
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layer = layer
                if raster_layer.providerType() != "wms":
                    path = raster_layer.source()
                    print("File raster layer:", path)
            else:
                return False  
        return True                        
    def copyErrLog(self):            
        filename = tempFile = tempfile.gettempdir() + os.sep + "import_log.txt"
        with open(filename, 'r') as file:
            file_contents = file.read()
        PyQt5.QtGui.QGuiApplication.clipboard().setText(file_contents)  
    def enableButtonImport(self, item, column):
        if (len(self.treeWidget.selectedItems()) > 0):
            self.pushButton.setEnabled(True)
        else:
            self.pushButton.setEnabled(False)        
            
    def initLogFile(self):
        filename = tempFile = tempfile.gettempdir() + os.sep + "import_log.txt"  
        if os.path.exists(filename):    
            open(filename, 'w').close()
        else:           
            open(filename, 'x').close()             
            
    def selectSelectedLayer(self):
        try:
            layer = self.layman.iface.activeLayer()
            layerName = layer.name()
        except:
            print("no layer in list")
            return
        iterator = QTreeWidgetItemIterator(self.treeWidget, QTreeWidgetItemIterator.All)
        while iterator.value():
            item = iterator.value()
            if item.text(0) == layerName:
                self.treeWidget.setCurrentItem(item, 1)
            iterator +=1            
            
    def disableExport(self):
        if self.treeWidget.selectedItems() == []:
            self.pushButton.setEnabled(False)
        else:
            self.pushButton.setEnabled(True)            
    def checkIfRasterInSelected(self):
        value = False
        for item in self.treeWidget.selectedItems():
            layer = QgsProject.instance().mapLayersByName(item.text(0))[0]
            if isinstance(layer, QgsRasterLayer):
                if self.utils.isBinaryRaster(layer):
                    text = "Nejbližší" if self.locale == "cs" else "nearest"
                else: 
                    text = "Není vybrán" if self.locale == "cs" else "No value"   
                self.comboBox_resampling.setCurrentText(text)
                value = True 
        self.comboBox_resampling.setEnabled(value)            
        
    def get_layers_in_order(self,node, layers):
        if isinstance(node, QgsLayerTreeLayer):
            layers.append(node.layer())
        elif isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                self.get_layers_in_order(child, layers)         
    def checkRegex(self, items, regex):
        for item in items:
            if not re.search(regex, item.text(0)):
                return False
        return True 
    def getRegex(self,string):       
        string = self.comboBox_layers.currentText()
        print(string)
        print(string)
        patterns =  [r'[0-9]{8}', r'[0-9]{8}T[0-9]{6}Z', r'([0-9]{8}T[0-9]{6})000(Z)', r'([0-9]{4}).([0-9]{2}).([0-9]{2})']
        for pattern in patterns:
            print(pattern)
            if re.search(pattern, string):
                print("Pattern found in the string.")
                self.lineEdit_regex.setText(pattern)   
        return False              
    def showTSDialog(self):                
        for item in self.treeWidget.selectedItems():
            self.comboBox_layers.addItem(item.text(0))
        self.pushButton_timeSeries.clicked.connect(lambda: self.prepareTSUpdate(self.treeWidget.selectedItems(), self.lineEdit_regex.text() , self.lineEdit_name.text()))    
        self.pushButton_backTime.clicked.connect(lambda: self.setStackWidget("main"))
        self.getRegex(self.treeWidget.selectedItems()[0].text(0))                
        
    def prepareTSUpdate(self, items, regex, title):
        resamplingMethod = self.comboBox_resampling.currentText()
        if not self.checkRegex(items, regex):
            print("regex nesedí na názvy")
            self.utils.emitMessageBox.emit(["Regulerní výraz nesedí na jeden nebo více názvů.", "The regular expression does not match one or more names."])
            return       
        self.progressBar.setMaximum(0)
        self.progressBar.show()
        self.label_progress.show()
        if self.locale == "cs":
            self.label_progress.setText("Úspěšně exportováno: 0 / 1")
        else:
            self.label_progress.setText("Sucessfully exported: 0 / 1")
        threading.Thread(target=lambda: self.layman.timeSeries(items, regex, title, resamplingMethod)).start()
                
    def checkExistingLayer(self, layerName):
        layerName = self.utils.removeUnacceptableChars(layerName)
        url = self.URI+'/rest/'+self.laymanUsername+"/layers"
        r = self.utils.requestWrapper("GET", url, payload = None, files = None)      
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