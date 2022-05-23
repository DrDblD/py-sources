import pandas as pd
import os

# print(os.path.dirname(os.path.realpath(__file__)))
_walker = os.walk(input().replace('"',''))
walk = "start"
while walk is not None:
    try:
        walk = next(_walker)
        root = walk[0]
        for file in walk[2]:
            if "csv" in file:
                pd.read_csv(os.path.join(root,file)).to_json(os.path.join(root,''.join([file,".json"])))
            else: 
                print(file)
    except StopIteration:
        break
