import threading        
import tempfile
import os
from qgis.core import QgsProject
from .qfield.cloud_converter import CloudConverter
import json
import urllib.parse

class Qfield:
    def __init__(self, utils): 
        self.utils = utils
        #self.URI = "https://qfield.lesprojekt.cz"
        self.URI = "http://localhost:8011"
        self.selectedLayers = []

    def createQProject(self, name, description, private):       
        url = self.URI + "/api/v1/projects/" 
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "is_public": private
        }   
        response = self.utils.requestWrapper("POST", url, payload = payload, files = None, emitErr = False)
        res = response.json()        
        if response.status_code == 201:
            self.uploadQFiles(res['id'], "")
        return response
        
        
    def convertQProject(self): 
        path = tempfile.mkdtemp(prefix="qfield_", dir=tempfile.gettempdir())
        cloud_convertor = CloudConverter(QgsProject.instance(), path, self.selectedLayers)
        cloud_convertor.convert()
        return path

    def uploadQFiles(self, project_id, path):
        layers = QgsProject.instance().mapLayers().values()
        if len(layers) == 0:
            self.utils.emitMessageBox(["Nejsou vrstvy k exportu!", "No layers to export!"])
            return
        mypath = self.convertQProject()        
        threading.Thread(target=lambda: self.postMultipleFiles(project_id, mypath)).start()
             
    

    def postMultipleFiles(self, project_id, directory_path):
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
            
    def getProjects(self):            
        url = f"{self.URI}/api/v1/projects/"
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=True)
        print(response.status_code)
        print(response.content)
        return response
                  
    def updateProjectPermissions(self, project_id, username, permissions):
        url = f"{self.URI}/api/v1/collaborators/{project_id}/{username}/"  
        response = self.utils.requestWrapper("PUT", url, payload=json.dumps(permissions), files=None, emitErr=True)
        return response

    def updateQfieldCloudPermissions(self, access_rights_json, project_id, existing_users):
        base_url = "{}/api/v1/collaborators/{}/{}/"  
        existing_users_set = set(existing_users)
        for role, users in access_rights_json['access_rights'].items():      
            qfield_role = "editor" if role == "write" else "reader"            
            for username in users:
                url = base_url.format(self.URI, project_id, username)
                # Update only if the user exists in QFieldCloud
                if username in existing_users_set:                 
                    data = {"role": qfield_role}                   
                    response = self.utils.requestWrapper("PUT", url, payload=json.dumps(data), files=None, emitErr=True) 
                    if response.status_code == 200:
                        print(f"Updated {username} to {qfield_role} successfully.")
                    else:
                        print(f"Failed to update {username}: {response.text}")

    def fetchExistingUsers(self):        
        url = f"{self.URI}/api/v1/users/"            
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=True)
        if response.status_code == 200:
            users_data = response.json()            
            return [user['username'] for user in users_data]
        else:
            print(f"Failed to fetch users: {response.text}")
            return []
        
    def getUserInfo(self):    
        url = f"{self.URI}/api/v1/auth/user/"          
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)      
        print(response.content)    
        return response        

    def getProjects(self):
        url = f"{self.URI}/api/v1/projects/"          
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)       
        return response   
    
    def getAllUsers(self):
        url = f"{self.URI}/api/v1/users/"          
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)       
        return response  
    
    def getPermissionsForProject(self, project_id):       
        url = f"{self.URI}/api/v1/collaborators/{project_id}/"          
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)       
        return response  
    
    def postPermissionsForProject(self, project_id, role, username):
        payload ={
        "collaborator": username,
        "role": role
        }
        print(payload)
        url = f"{self.URI}/api/v1/collaborators/{project_id}/"  
        print(url)
        response = self.utils.requestWrapper("POST", url, payload=payload, files=None, emitErr=False)     
        print(response.content) 
        return response
    
    def putPermissionsForProject(self, project_id, role, username):  
        payload ={
        "role": role
        }
        username = self.checkIfGroup(username)
        url = f"{self.URI}/api/v1/collaborators/{project_id}/{username}/"  
        response = self.utils.requestWrapper("PUT", url, payload=payload, files=None, emitErr=False)       
        return response   
    
    def patchPermissionsForProject(self, project_id, role, username):        
        payload ={
        "collaborator": username,    
        "role": role
        }
        username = self.checkIfGroup(username)
        url = f"{self.URI}/api/v1/collaborators/{project_id}/{username}/"  
        response = self.utils.requestWrapper("PATCH", url, payload=payload, files=None, emitErr=False)       
        return response 
    
    def deletePermissionsForProject(self, project_id, username):      
        url = f"{self.URI}/api/v1/collaborators/{project_id}/{username}/"  
        response = self.utils.requestWrapper("DELETE", url, payload=None, files=None, emitErr=False)       
        return response 
    
    def getProjectFiles(self, project_id):      
        url = f"{self.URI}/api/v1/files/{project_id}/"  
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)       
        return response 
    
    def getProjectFile(self, project_id, filename):      
        url = f"{self.URI}/api/v1/files/{project_id}/{filename}/"  
        response = self.utils.requestWrapper("GET", url, payload=None, files=None, emitErr=False)       
        return response 
    
    def postProjectFile(self, project_id, filename): 
        fullname = filename
        filename = self.utils.get_filename_without_extension(filename)
        files = {
            'file': (filename, open(fullname, 'rb'))
        }   
        url = f"{self.URI}/api/v1/files/{project_id}/{filename}/"  
        response = self.utils.requestWrapper("POST", url, payload=None, files=files, emitErr=False)         
        return response 
    
    def deleteProjectFile(self, project_id, filename):      
        url = f"{self.URI}/api/v1/files/{project_id}/{filename}/"  
        response = self.utils.requestWrapper("DELETE", url, payload=None, files=None, emitErr=False)       
        return response 
    def deleteProject(self, project_id):
        url = f"{self.URI}/api/v1/projects/{project_id}/"  
        response = self.utils.requestWrapper("DELETE", url, payload=None, files=None, emitErr=False)       
        return response 
    def findProjectByName(self, project_name):
        projects = self.getProjects().json()
        for project in projects:
            if project['name'] == project_name:
                return project['id']
        return None 
    def checkIfGroup(self, username):
        if "@" in username:
            return "roles"
        else:
            return username
        
    def findLayersToPost(self, local_layers, server_layers):      
        server_layer_names = {layer['name'] for layer in server_layers}       
        layers_to_upload = [layer["title"] for layer in local_layers if layer['title'] not in server_layer_names]
        return layers_to_upload

    def findLayersToDelete(self, local_layers, server_layers):       
        server_layer_names = {layer['name'] for layer in server_layers}
        layers_to_delete = [layer["title"] for layer in server_layer_names if layer not in local_layers]
        return layers_to_delete  
    
    def findLayersToDelete(self, local_layers, server_layers):   
        local_layer_titles = {layer['title'] for layer in local_layers}   
        layers_to_delete = [layer['name'] for layer in server_layers if layer['name'] not in local_layer_titles]        
        return layers_to_delete

    def findLayersToCheck(local_layers, server_layers):  
        server_gpkg_layers = {layer['name'] for layer in server_layers if layer['name'].endswith('.gpkg')}  
        gpkg_layers_to_check = [layer for layer in local_layers if layer.endswith('.gpkg') and layer in server_gpkg_layers]    
        return gpkg_layers_to_check        
    
    def filesToCheck(self, server_layers):      
        extensions = ('.gpkg', '.zip', '.qgs', '.qgz', '.qgs~')        
        server_files_hashes = {}
        for layer in server_layers:
            if layer['name'].endswith(extensions):                
                for version in layer['versions']:
                    if version['is_latest']:
                        server_files_hashes[layer['name']] = version['md5sum']
        return server_files_hashes
    def getProjectByName(self, name):
        project_list = self.getProjects().json()
        for project in project_list:
            if project['name'] == name:
                return project['id']
        return None 