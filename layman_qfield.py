import threading        
import tempfile
import os
from qgis.core import QgsProject
from .qfield.cloud_converter import CloudConverter

class Qfield:
    def __init__(self, utils): 
        self.utils = utils
        #self.URI = "https://qfield.lesprojekt.cz"
        self.URI = "http://localhost:8011"

    def createQProject(self, name, description, private):
        url = self.URI + "/api/v1/projects/" 
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "is_public": private
        }   
        response = self.utils.requestWrapper("POST", url, payload = payload)
        res = response.json()        
        if response.status_code == 201:
            self.uploadQFiles(res['id'], "")
        return response
        
        
    def convertQProject(self): 
        path = tempfile.mkdtemp(prefix="qfield_", dir=tempfile.gettempdir())
        cloud_convertor = CloudConverter(QgsProject.instance(), path)
        cloud_convertor.convert()
        return path

    def uploadQFiles(self, project_id, path):
        layers = QgsProject.instance().mapLayers().values()
        if len(layers) == 0:
            self.utils.emitMessageBox(["Nejsou vrstvy k exportu!", "No layers to export!"])
            return
        mypath = self.convertQProject()        
        threading.Thread(target=lambda: self.post_multiple_files(project_id, mypath)).start()
             
   

    def post_multiple_files(self, project_id, directory_path):
        url = f"{self.URI}/api/v1/files/{project_id}/"
        files_to_upload = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]  
        multipart_files = {}  
        for file_path in files_to_upload:
            file_name = os.path.basename(file_path)
            multipart_files['file'] = (file_name, open(file_path, 'rb'), 'application/octet-stream')                
            response = self.utils.requestWrapper("POST", url + file_name + "/", payload=None, files=multipart_files, emitErr=True)
            if response.ok:
                print(f"Soubor {file_name} byl úspěšně nahrán")
            else:
                print(f"Chyba při nahrávání souboru {file_name}:", response.text)           

            multipart_files['file'][1].close()
            