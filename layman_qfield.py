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
        print(res)
        if response.status_code == 201:
            self.uploadQFiles(res['id'], "")
        return res
        
        # else:
        #     self.utils.emitMessageBox(["Taková kompozice již existuje. Vyberte prosím jiný název.", "This composition already exists. Please choose another name."])

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

    # def postQData(self, project_id, mypath):
    #     for root, _, filenames in os.walk(mypath):
    #         for filename in filenames:
    #             file_path = os.path.join(root, filename)
    #             with open(file_path, 'rb') as file:
    #                 files = {
    #                     'file': (filename, file, 'application/octet-stream')
    #                 }               
    #                 #url = f"{self.URI}/api/v1/projects/{project_id}/files/{filename}/"
    #                 url = f"{self.URI}/api/v1/files/{project_id}/{filename}/"
    #                 # response = requests.post(url, headers=headers, files=files)
    #                 response = self.utils.requestWrapper("POST", url, payload= None, files=files)
    #                 if response.status_code == 200:
    #                     print("Soubor byl úspěšně nahrán")
    #                 else:
    #                     print("Chyba při nahrávání souboru:", response.text)
    #                     break 
    def postQData(self, project_id, mypath):        
        payload={}     
        filepaths = []
        f = []
        for (dirpath, dirnames, filenames) in os.walk(mypath):
            f.extend(filenames)
            break
        for files in f:
            filepaths.append(mypath + os.sep+files)
        
        for i in range (0,len(filepaths)):

            files=[
              ('file',(f[i],open(filepaths[i],'rb'),'application/octet-stream'))              
            ]           
           
            url = self.URI +"/api/v1/files/" + project_id+ "/" +f[i] + "/"          
            print(url)
                       
            response = self.utils.requestWrapper("POST", url, payload=None,  files=files)      
            print(response.content)              
   

    def post_multiple_files(self, project_id, directory_path):
        url = f"{self.URI}/api/v1/files/{project_id}/"

        # Získání seznamu cest k souborům v daném adresáři
        files_to_upload = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

        # Příprava multipart_files pro nahrávání
        multipart_files = {}
        for file_path in files_to_upload:
            file_name = os.path.basename(file_path)
            multipart_files['file'] = (file_name, open(file_path, 'rb'), 'application/octet-stream')
            
            # Odeslání požadavku pro každý soubor
            response = self.utils.requestWrapper("POST", url + file_name + "/", payload=None, files=multipart_files)

            # Kontrola výsledku
            if response.ok:
                print(f"Soubor {file_name} byl úspěšně nahrán")
            else:
                print(f"Chyba při nahrávání souboru {file_name}:", response.text)
            
            # Uzavření souboru po jeho odeslání
            multipart_files['file'][1].close()
            