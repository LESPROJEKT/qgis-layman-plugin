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
import threading
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from qgis.core import Qgis



# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dlg_addMicka.ui'))


class AddMickaDialog(QtWidgets.QDialog, FORM_CLASS):
    progressDone = pyqtSignal()
    def __init__(self, uri,utils, layman, parent=None):
        """Constructor."""
        super(AddMickaDialog, self).__init__(parent)
        self.cataloguePosition = 1     
        self.utils = utils
        self.layman = layman
        self.URI = uri
        self.setupUi(self)
        self.setUi()        
        self.connectEvents()
        
    def setUi(self):    
        self.cataloguePosition = 1
        self.progressDone.emit()
        self.loadMickaMaps()
        self.pushButton_map.clicked.connect(lambda: self.progressBar_loader.show())
        self.pushButton_map.clicked.connect(lambda: self.layman.loadLayersMicka(self.treeWidget.selectedItems()[0].text(0),self.treeWidget.indexOfTopLevelItem(self.treeWidget.currentItem()), self.mickaRet))
        self.pushButton_stepLeft.clicked.connect(lambda: self.goLeft())
        self.pushButton_stepRight.clicked.connect(lambda: self.goRight())
        self.pushButton_search.clicked.connect(lambda: self.mickaSearch())
        self.pushButton_close.clicked.connect(lambda: self.close())
        self.show()   
    def connectEvents(self):
        self.progressDone.connect(self._onProgressDone)    
    def goLeft(self):
        print(self.cataloguePosition)
        if self.cataloguePosition > 30:
            self.cataloguePosition = self.cataloguePosition - 20
            self.loadMickaMaps()
        else:
            self.cataloguePosition = self.cataloguePosition = 1
            self.loadMickaMaps()
    def goRight(self):
        if self.cataloguePosition < 500:            
            self.cataloguePosition = self.cataloguePosition + 20           
            self.loadMickaMaps()
        else:
            self.utils.emitMessageBox.emit(["Není možné listovat doprava!", "Not possible page to right!"])   
    
                
    def mickaSearch(self):
        query = self.lineEdit_search.text()     
        self.loadMickaMaps(query)

    def loadMickaMaps(self, query = ""):
        self.progressBar_loader.show()        
        self.treeWidget.clear()         
        threading.Thread(target=lambda: self.loadMickaMapsThread(query)).start()
        
    def loadMickaMapsThread(self, query = ""):  
        uri = self.URI.replace("/client", "")       
        if query == "":
            #url = uri + "/micka/csw/?request=GetRecords&query=type%3D%27application%27&format=text/json&MaxRecords=20&StartPosition="+str(self.cataloguePosition)+"&sortby=&language=eng&template=report-layman"           
            url = uri + "/micka/csw/?request=GetRecords&query=type%3D%27application%27&format=text/json&MaxRecords=20&StartPosition="+str(self.cataloguePosition)+"&sortby=&language=eng"           
        else:
            #url = uri + "/micka/csw/?request=GetRecords&query=AnyText%20like%20%27*"+query+"*%27%20AND%20type%3D%27application%27&format=text/json&MaxRecords=10&StartPosition=&sortby=&language=eng&template=report-layman"            
            url = uri + "/micka/csw/?request=GetRecords&query=AnyText%20like%20%27*"+query+"*%27%20AND%20type%3D%27application%27&format=text/json&MaxRecords=10&StartPosition=&sortby=&language=eng"            
        r = self.utils.requestWrapper("GET", url, payload = None, files = None) 
        self.mickaRet = r.json()    
        try:
            self.mickaRet = r.json() 
        except:            
            self.utils.showQBar.emit(["Micka není k dispozici","Micka is not available"], Qgis.Warning)             
            return   
        
        for record in self.mickaRet['records']:          
            if "title" in record:
                item = QTreeWidgetItem([record['title']])
                self.treeWidget.addTopLevelItem(item)     
        self.progressDone.emit()
    def _onProgressDone(self):
        try:
            self.progressBar_loader.hide()
        except:
            pass   