import json
import yaml

# kubectl images -A -o json

def aint(mlist, member):
    if member is None:
        return mlist
    if member in mlist:
        return mlist
    else:
        return mlist + [member]


file_json = input("path?:\t")
image_list = json.loads(open(file_json, "r").read())
used_image = {}
for image in image_list:
    if not used_image.get( image["Image"], False ):
        used_image[image["Image"]]={"Pods": [], "Namespaces": [], "Containers": []}
    
    used_image[image["Image"]]["Pods"] = aint( 
        used_image[image["Image"]]["Pods"],
        image["Pod"])

    used_image[image["Image"]]["Namespaces"] = aint( 
        used_image[image["Image"]]["Namespaces"],
        image["Namespace"])

    used_image[image["Image"]]["Containers"] = aint( 
        used_image[image["Image"]]["Containers"], 
        { image["Container"]: image["ImagePullPolicy"] })

yaml.safe_dump(used_image,open(file_json+".yaml", "w"))