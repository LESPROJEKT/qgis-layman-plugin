# QGIS Client usable for importing map layers to Layman server  

## OAuth2 login
For usage of this plugin is needed account at www.agrihub.cz and agrihub ID. There is implemented OAuth2 authentification. Authentization is processed in Agrihub login form. There is user redirected.
Email in plugin part is used as name for creating new Layman user if not exists. Authentication is valid only 10 minutes. Due this fact plugin every 10 minutes renew authentication tokens.    

## After sucessfull autentization functions are unlocked and you are able to:
### Load, Save vector layers in JSON format on local pc.    
It provides simple forms for loading data. SLD file with symbology is also stored with same name like JSON file.

### Import vector layer to Layman server. 
In case size of layer is bigger than 1MB is layer automaticaly parted and send asynchronously. It is usable for bigger layers when importing fails. Plugin is able to establish uploading at point of failure. 
EPSG: 4326 is allowed.
From every layer is generated and imported SLD file, that keeps layer symbology. 

### Load existing layer from Layman to QGIS.  
Layers are loaded as WMS service to QGIS layer tree. Layer thumbnail is loaded into form. 

### Create map composite and save to Layman server.   
For creating composite is necessary fill all mandatory fields (name, title, description). This information is stored in composition file. There are also required specify the extent of the map. Extend can be automatically assumed from existing layer. 

### Add, delete layers to map composite.  
User can use new local layers and also existing layers in Layman. For working with compositions is prepaired main form with all functionalities.

### Delete map composites from memory/server.  

### Load all map composites to QGIS.  
After loading existing composition from Layman are layers ordered to group in QGIS layer tree. One composition can be loaded only once. Composition name is unique. Map thumbnail is loaded into form. 
 

 

