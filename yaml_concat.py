import yaml
import sys
import os 
import collections.abc

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

file_path = "inventory/targets"
dir = "/".join([file_path, sys.argv[1]])
_walker = os.walk(dir.replace('"',''))
walk = next(_walker)
data = {}
while walk is not None:
    try:
        root = walk[0]
        for file in walk[2]:
            with open(os.path.join(root,file), 'r') as yaml_input:
                data = update(data, yaml.safe_load(yaml_input)) if data else yaml.safe_load(yaml_input)
        walk = next(_walker)
    except StopIteration:
        break

with open(".".join([dir,"yaml"]), 'w') as yaml_output:
    yaml.dump(data, yaml_output, allow_unicode=True)