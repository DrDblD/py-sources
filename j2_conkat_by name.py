import os
import yaml
import re
import collections
# from jinja2 import Template, Environment, BaseLoader

file_path = input("PAth:\t")
name_f = "application.yml"
# name_f = input("file name:\t")

_walker = os.walk(file_path.replace('"',''))

def update(d, u):
    if u:
        if d:
            for k, v in u.items():
                if isinstance(v, collections.abc.Mapping):
                    d[k] = update(d.get(k, {}), v)
                else:
                    d[k] = v
        else:
            return u
    return d

walk = next(_walker)
data = {}
# env = Environment(loader=BaseLoader)

while walk is not None:
    try:
        root = walk[0]
        for file in walk[2]:
            if name_f in file:
                with open(os.path.join(root,file), 'r') as ifile:
                    # template = Template(ifile.read())
                    # print(template.)
                    yaml_input = "".join([re.sub(r'\{\{.*\}\}', '', re.sub(r'^{%[\w =]+%}$', '', line)) for line in ifile.readlines() ])
                    data = update(data, yaml.safe_load(yaml_input)) if data else yaml.safe_load(yaml_input)
        walk = next(_walker)
    except StopIteration:
        break

with open(".".join([file_path,"yaml"]), 'w') as yaml_output:
    yaml.dump(data, yaml_output, allow_unicode=True)