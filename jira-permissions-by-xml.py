# from xml2yaml import parseXml
import sys
import pandas as pd
import xmltodict

def dict2html(list):
    text = pd.melt(pd.DataFrame(list)).to_html()
    return text

args = sys.argv
path = args[1] if len(args) > 1 else input('path:\t')
datadict = xmltodict.parse(open(path,"r",  encoding="utf-8").read(), encoding='utf-8')

# print(datadict.keys())
# # print(datadict["workflow"]["steps"]["step"])
steps = datadict["workflow"]["steps"]["step"]

common_actions = dict(zip(
    [x["@id"] for x in datadict["workflow"]["common-actions"]["action"]],
    [{ "@name": x["@name"], "meta": x["meta"]} for x in datadict["workflow"]["common-actions"]["action"]]
    ))
# print(common_actions)
# df = pd.DataFrame()
# df = pd.DataFrame.from_dict(steps)
# ndf = pd.melt(df)
# ndf = df.fillna(' ').T
# print(ndf)
# text = ndf.to_html()

text = ""
findict = {}
groups = []
for step in steps:
    # text += dict2html(meta)
    for i in step["meta"]:
        if "permission" in i["@name"]:
            if i["#text"] in list(findict.keys()):
                if step["@name"] in list(findict[i["#text"]].keys()):
                    findict[i["#text"]][step["@name"]]["permissions"].append(i["@name"])
                else:
                    findict[i["#text"]].update({
                        step["@name"]:{
                            "permissions": [i["@name"]]
                        }
                    })
            else:                
                findict.update({
                    i["#text"] : {
                        step["@name"]:{
                            "permissions": [i["@name"]]
                        }
                    }
                })
    actions = []
    if "common-action" in step["actions"].keys():
        for action in step["actions"]["common-action"]:
            if type(action) == type({}):
                if len(list(action.keys())) > 1:
                    actions.append(common_actions[action["@id"]])
    if "action" in step["actions"].keys():
        for action in step["actions"]["action"]:
            if type(action) == type({}):
                if len(list(action.keys())) > 1:
                    actions.append(action)
    
    for action in actions:
        if "permission" in i["@name"]:
            if i["#text"] in list(findict.keys()):
                if step["@name"] not in list(findict[i["#text"]].keys()):
                    findict[i["#text"]].update({
                        step["@name"]:{}
                    })
            else:                
                findict.update({
                    i["#text"] : {
                        step["@name"]:{}
                    }
                })
            
            if "actions" not in list(findict[i["#text"]][step["@name"]].keys()):
                findict[i["#text"]][step["@name"]].update({
                    "actions": {}
                })
            if action["@name"] in list(findict[i["#text"]][step["@name"]]["actions"].keys()):
                if "permissions" in list(findict[i["#text"]][step["@name"]]["actions"][action["@name"]].keys()):
                    findict[i["#text"]][step["@name"]]["actions"][action["@name"]]["permissions"].append(i["@name"])
                else:
                    findict[i["#text"]][step["@name"]]["actions"][action["@name"]].update({
                        "permissions": [i["@name"]]
                    })
            else:
                findict[i["#text"]][step["@name"]]["actions"].update({
                    action["@name"]: {
                        "permissions": [i["@name"]]
                    }
                })

for group in findict:        
    text += "\n<br><h1>" + group + "</h1><br>\n"
    for step in findict[group]:
        text += "\n<br><h2>" + step + "</h2><br>\n"
        df = pd.DataFrame()
        df = pd.json_normalize(findict[group][step])
        ndf = df.fillna(' ').T
        text += ndf.to_html()

open(path + ".html", "w").write(text)