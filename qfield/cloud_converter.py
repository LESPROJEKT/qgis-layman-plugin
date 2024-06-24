# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QFieldSync
                              -------------------
        begin                : 2021-07-20
        git sha              : $Format:%H$
        copyright            : (C) 2021 by OPENGIS.ch
        email                : info@opengis.ch
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

from pathlib import Path

from libqfieldsync.layer import LayerSource
from libqfieldsync.utils.file_utils import copy_attachments
from libqfieldsync.utils.qgis import get_qgis_files_within_dir, make_temp_qgis_file
from qgis.core import QgsMapLayer, QgsProject, QgsVirtualLayerDefinition, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QObject, QUrl, pyqtSignal
from qgis.utils import iface
# from .qgis_utils import open_project
from qgis.PyQt.QtXml import QDomDocument


from qgis.core import QgsVectorFileWriter, QgsProject, QgsReadWriteContext
import os
from qgis.core import  QgsCoordinateTransformContext, QgsFields


class CloudConverter(QObject):
    progressStopped = pyqtSignal()
    warning = pyqtSignal(str, str)
    total_progress_updated = pyqtSignal(int, int, str)

    def __init__(
        self,
        project: QgsProject,
        export_dirname: str,
        selectedLayers: list,
    ):

        super(CloudConverter, self).__init__(parent=None)
        self.project = project
        self.__layers = list()

        # elipsis workaround
        self.trUtf8 = self.tr

        self.export_dirname = Path(export_dirname)
        self.selectedLayers = selectedLayers

    
 
    def convert(self) -> None:  # noqa: C901
        """
        Convert the project to a cloud project.
        """

        original_project_path = self.project.fileName()
        project_path = self.export_dirname.joinpath(
            f"{self.project.baseName()}_cloud.qgs"
        )
        backup_project_path = make_temp_qgis_file(self.project)
        print(backup_project_path)
        is_converted = False

        try:
            if not self.export_dirname.exists():
                self.export_dirname.mkdir(parents=True, exist_ok=True)

            if get_qgis_files_within_dir(self.export_dirname):
                raise Exception(
                    self.tr("The destination folder already contains a project file")
                )

            self.total_progress_updated.emit(0, 100, self.trUtf8("Converting project…"))
            self.__layers = list(self.project.mapLayers().values())           
            # Loop through all layers and copy them to the destination folder
            for current_layer_index, layer in enumerate(self.__layers):
                if not layer.name() in self.selectedLayers:
                    continue
                self.total_progress_updated.emit(
                    current_layer_index,
                    len(self.__layers),
                    self.trUtf8("Copying layers…"),
                )

                layer_source = LayerSource(layer)
                if not layer_source.is_supported:
                    continue

                if layer.dataProvider() is not None:
                    if layer_source.is_localized_path:
                        continue

                if layer.type() == QgsMapLayer.VectorLayer:
                    if (
                        layer.dataProvider()
                        and layer.dataProvider().name() == "virtual"
                    ):
                        url = QUrl.fromEncoded(layer.source().encode("ascii"))
                        valid = url.isValid()
                        if valid:
                            definition = QgsVirtualLayerDefinition.fromUrl(url)
                            for source in definition.sourceLayers():
                                if not source.isReferenced():
                                    valid = False
                                    break
                        if not valid:
                            self.warning.emit(
                                self.tr("Cloud Converter"),
                                self.tr(
                                    "The virtual layer '{}' is not valid or contains non-referenced source(s) and could not be converted and was therefore removed from the cloud project."
                                ).format(layer.name()),
                            )
                            continue
                    elif layer.dataProvider().name() == "WFS":
                        # Skip WFS layers, do not convert them
                        continue
                    else:
                        if not layer_source.convert_to_gpkg(self.export_dirname):
                            self.warning.emit(
                                self.tr("Cloud Converter"),
                                self.tr(
                                    "The layer '{}' could not be converted and was therefore removed from the cloud project."
                                ).format(layer.name()),
                            )
                            continue
                else:
                    layer_source.copy(self.export_dirname, list())
                layer.setCustomProperty(
                    "QFieldSync/cloud_action", layer_source.default_cloud_action
                )

            if not self.project.write(str(project_path)):
                raise Exception(
                    self.tr('Failed to save project to "{}".').format(project_path)
                )

            for attachment_dir in ["DCIM"]:
                copy_attachments(
                    Path(original_project_path).parent,
                    project_path.parent,
                    attachment_dir,
                )

            title = self.project.title()
            title_suffix = self.tr("(QFieldCloud)")
            if not title.endswith(title_suffix):
                self.project.setTitle("{} {}".format(title, title_suffix))
            self.project.write(str(project_path))
            is_converted = True
        finally:
            QCoreApplication.processEvents()
            QCoreApplication.processEvents()

            if is_converted:
                pass
            else:
                pass    
            # open_project(original_project_path, backup_project_path)

        self.total_progress_updated.emit(100, 100, self.tr("Finished"))
