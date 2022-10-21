import time
import requests
from getpass import getpass
import os
import tempfile
import re
import zipfile
import urllib.parse
import logging
import yaml
import sys


query_list = { 
    "search": {
        "id": "uuid",
    "queries": [
        "object"
    ],
    "parameters": [
        "object"
    ],
    "owner": "string",
    "created_at": "string",
    "requires": "object"
}}

def httpRequestWrapper(func):
    def wrapper(*args,**kwargs):
        begin = time.time()
        try:
            output = func(*args,**kwargs)
            end = time.time()
            return output
        except requests.exceptions.HTTPError as err:
            # raise SystemExit(err)
            end = time.time()
            logging.error("Total time taken in {}: {}".format(func.__name__, end - begin))
            logging.error(err)
    return wrapper


def paginated_get(url=str(),headers=dict(),params=dict(),exit_query=False):
    output = []
    params["per_page"] = 50
    r = requests.get(url=url, headers=headers,params=params)
    r.raise_for_status()
    output += r.json()
    next_page=int(r.headers["x-next-page"])
    logging.debug(r.headers["x-total-pages"])
    for i in range(next_page, int(r.headers["x-total-pages"])):
        if exit_query:
            if exit_query(output):
                logging.debug("exit query break")
                break
        params["page"]=next_page
        req = requests.get(url=url, headers=headers, params=params)
        output += req.json()
        next_page=req.headers["x-next-page"]
    return output

@httpRequestWrapper
def get_raw_file(token,root,rest,project_id,payload={"ref": "master"},fname=".gitlab-ci.yml",output="."):
    url = "https://{}/{}/projects/{}/repository/files/{}/raw".format(
        root,
        rest,
        project_id,
        urllib.parse.quote(fname, safe='').replace("-","%2D").replace(".","%2E")
    )
    logging.debug(url)
    headers = { "PRIVATE-TOKEN": token }
    with requests.get(
        url=url,
        headers=headers,
        params=payload,
        stream=True
    ) as r:
        r.raise_for_status()
        with open(os.path.join(output,fname), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return True