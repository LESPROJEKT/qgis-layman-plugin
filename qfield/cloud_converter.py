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

from qfieldsync.core.preferences import Preferences
from qfieldsync.utils.qgis_utils import open_project
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
                #     self.project.removeMapLayer(layer)
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
                            # virtual layers with non-referenced sources are not supported
                            self.warning.emit(
                                self.tr("Cloud Converter"),
                                self.tr(
                                    "The virtual layer '{}' is not valid or contains non-referenced source(s) and could not be converted and was therefore removed from the cloud project."
                                ).format(layer.name()),
                            )
                            # self.project.removeMapLayer(layer)
                            continue
                    else:
                        if not layer_source.convert_to_gpkg(self.export_dirname):       
                            # something went wrong, remove layer and inform the user that layer will be missing
                            self.warning.emit(
                                self.tr("Cloud Converter"),
                                self.tr(
                                    "The layer '{}' could not be converted and was therefore removed from the cloud project."
                                ).format(layer.name()),
                            )
                            # self.project.removeMapLayer(layer)
                            continue
                else:
                    layer_source.copy(self.export_dirname, list())
                layer.setCustomProperty(
                    "QFieldSync/cloud_action", layer_source.default_cloud_action
                )

            # save the offline project twice so that the offline plugin can "know" that it's a relative path
            if not self.project.write(str(project_path)):
                raise Exception(
                    self.tr('Failed to save project to "{}".').format(project_path)
                )

            # export the DCIM folder
            for attachment_dir in Preferences().value("attachmentDirs"):
                copy_attachments(
                    Path(original_project_path).parent,
                    project_path.parent,
                    attachment_dir,
                )

            title = self.project.title()
            title_suffix = self.tr("(QFieldCloud)")
            if not title.endswith(title_suffix):
                self.project.setTitle("{} {}".format(title, title_suffix))
            # Now we have a project state which can be saved as cloud project
            self.project.write(str(project_path))
            is_converted = True
        finally:
            # We need to let the app handle events before loading the next project or QGIS will crash with rasters
            QCoreApplication.processEvents()
            # self.project.clear()
            QCoreApplication.processEvents()

            # TODO whatcha gonna do if QgsProject::read()/write() fails
            if is_converted:
                pass
                # iface.addProject(str(project_path))
            else:
                pass    
            open_project(original_project_path, backup_project_path)

        self.total_progress_updated.emit(100, 100, self.tr("Finished"))
 

# class CustomLayerSource(LayerSource):
   
#     def convert_to_gpkg(self, target_path):
#         """
#         Convert a layer to geopackage in the target path and adjust its datasource. If
#         a layer is already a geopackage, the dataset will merely be copied to the target
#         path.

#         :param layer: The layer to copy
#         :param target_path: A path to a folder into which the data will be copied
#         :param keep_existent: if True and target file already exists, keep it as it is
#         """

#         if not self.layer.type() == QgsMapLayer.VectorLayer or not self.layer.isValid():
#             return

#         file_path = self.filename
#         suffix = ""
#         uri_parts = self.layer.source().split("|", 1)
#         print(uri_parts)        
#         if len(uri_parts) > 1:
#             suffix = uri_parts[1]

#         dest_file = ""
#         new_source = ""
#         # check if the source is a geopackage, and merely copy if it's the case
#         if (
#             os.path.isfile(file_path)
#             and self.layer.dataProvider().storageType() == "GPKG"
#         ):
#             source_path, file_name = os.path.split(file_path)
#             dest_file = os.path.join(target_path, file_name)
#             if not os.path.isfile(dest_file):
#                 shutil.copy(os.path.join(source_path, file_name), dest_file)

#             if self.provider_metadata is not None:
#                 metadata = self.metadata
#                 metadata["path"] = dest_file
#                 new_source = self.provider_metadata.encodeUri(metadata)

#             if new_source == "":
#                 new_source = os.path.join(target_path, file_name)
#                 if suffix != "":
#                     new_source = "{}|{}".format(new_source, suffix)

#         layer_subset_string = self.layer.subsetString()
#         if new_source == "":
#             pattern = re.compile(r"[\W_]+")  # NOQA
#             cleaned_name = pattern.sub("", self.layer.name())
#             dest_file = os.path.join(target_path, "{}.gpkg".format(cleaned_name))
#             suffix = 0
#             while os.path.isfile(dest_file):
#                 suffix += 1
#                 dest_file = os.path.join(
#                     target_path, "{}_{}.gpkg".format(cleaned_name, suffix)
#                 )

#             # clone vector layer and strip it of filter, joins, and virtual fields
#             source_layer = self.layer.clone()
#             source_layer.setSubsetString("")
#             source_layer_joins = source_layer.vectorJoins()
#             for join in source_layer_joins:
#                 source_layer.removeJoin(join.joinLayerId())
#             fields = source_layer.fields()
#             virtual_field_count = 0
#             for i in range(0, len(fields)):
#                 if fields.fieldOrigin(i) == QgsFields.OriginExpression:
#                     source_layer.removeExpressionField(i - virtual_field_count)
#                     virtual_field_count += 1

#             options = QgsVectorFileWriter.SaveVectorOptions()
#             options.fileEncoding = "UTF-8"
#             options.driverName = "GPKG"
#             (error, returned_dest_file) = QgsVectorFileWriter.writeAsVectorFormatV2(
#                 source_layer, dest_file, QgsCoordinateTransformContext(), options
#             )
#             if error != QgsVectorFileWriter.NoError:
#                 return
#             if returned_dest_file:
#                 new_source = returned_dest_file
#             else:
#                 new_source = dest_file

#         self._change_data_source(new_source, "ogr")
#         if layer_subset_string:
#             self.layer.setSubsetString(layer_subset_string)

#         return dest_file

#     def _change_data_source(self, new_data_source, new_provider=None):
#         """
#         Changes the datasource string of the layer
#         """
#         context = QgsReadWriteContext()
#         document = QDomDocument("style")
#         map_layers_element = document.createElement("maplayers")
#         map_layer_element = document.createElement("maplayer")
#         self.layer.writeLayerXml(map_layer_element, document, context)

#         # modify DOM element with new layer reference
#         map_layer_element.firstChildElement("datasource").firstChild().setNodeValue(
#             new_data_source
#         )
#         map_layers_element.appendChild(map_layer_element)
#         document.appendChild(map_layers_element)

#         if new_provider:
#             map_layer_element.firstChildElement("provider").setAttribute(
#                 "encoding", "UTF-8"
#             )
#             map_layer_element.firstChildElement("provider").firstChild().setNodeValue(
#                 new_provider
#             )

#         # reload layer definition
#         self.layer.readLayerXml(map_layer_element, context)
#         self.layer.reload()