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
def get_groups(token,root,rest):
    url = "https://{}/{}/groups".format(root,rest)
    headers = { "PRIVATE-TOKEN": token }
    r = paginated_get(url=url, headers=headers)
    return r

@httpRequestWrapper
def get_group_projects(token,root,rest,group_id):
    url = "https://{}/{}/group/{}/projects".format(root,rest,group_id)
    headers = { "PRIVATE-TOKEN": token }
    r = paginated_get(url=url, headers=headers)
    return r

@httpRequestWrapper
def get_projects(token,root,rest):
    url = "https://{}/{}/projects".format(root,rest)
    headers = { "PRIVATE-TOKEN": token }
    r = paginated_get(url=url, headers=headers)
    return r

@httpRequestWrapper
def get_jobs(token,root,rest,project_id):
    url = "https://{}/{}/projects/{}/jobs".format(root, rest, project_id)
    headers = { "PRIVATE-TOKEN": token }
    r = paginated_get(url=url, headers=headers)
    return r

@httpRequestWrapper
def find_job(token,root,rest,project_id,job_name_list):
    url = "https://{}/{}/projects/{}/jobs".format(root, rest, project_id)
    headers = { "PRIVATE-TOKEN": token }
    exit_query =lambda x: True if set(job_name_list).issubset(set([
                    job["name"]                    
                    for job in x
                    if job["status"] == "success" and job["name"] in job_name_list
                ])) else False
    payload = {"scope": "success"}
    r = paginated_get(url=url, headers=headers, params=payload, exit_query=exit_query)
    output = [job for job in r if job["status"] == "success" and job["name"] in job_name_list]
    logging.debug(output)
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

@httpRequestWrapper
def get_artifacts(token,root,rest,project_id,job_id,fname="artifacts.zip"):
    url = "https://{}/{}/projects/{}/jobs/{}/artifacts".format(root, rest, project_id, job_id )
    headers = { "PRIVATE-TOKEN": token }
    with requests.get(
        url=url,
        headers=headers,
        stream=True
    ) as r:
        if r.status_code == 404:
            return None
        r.raise_for_status()
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return fname


def deepFindAll(self=dict(), key=str()):
    def list_add(listed,item):
        if type(item) == type([]): 
            listed += item
        else:
            listed.append(item)
        return listed            
    if type(self) == type({}):
        listed_out = []
        getter = self.get(key, False)
        if getter: listed_out = list_add(listed_out, getter)
        for k in self:
            v = self[k]
            if type(v) == type({}):
                getter = v.get(key, False)
                if getter:
                    listed_out = list_add(listed_out, getter)
                else:
                    listed_out = list_add(listed_out, deepFindAll(v, key))
        return listed_out


def get_images_from_pipeline(pipefile,images,jobs):
    pipetext = "".join(pipefile)
    pipeline = yaml.safe_load(pipetext)
    image_keys = deepFindAll(pipeline, "image")
    trigger_keys = deepFindAll(pipeline, "trigger")
    if trigger_keys:
        for key in trigger_keys:
            includes = deepFindAll(key, "include")
            if includes:
                for include in includes:
                    jobs.append(include["job"])
    output = []
    if image_keys:
        for key in image_keys:
            if type(key)==type({}):
                output.append(key["name"])
            else:
                output.append(key)
    for image in output:
        logging.info(image)
    images += output
    return images, jobs

def menu(args):
    def help():
        help = "usage -t token [-h][-l][-o][-v] \n"\
        "\t-h \"gitlab host\"\tuse this option to define the gitlab host\n"\
        "\t\t\t\tdefault gitlab host is \"gitlab.com\"\n"\
        "\t-t \"gitlab token\"\tuse this option to define the gitlab tocken \n"\
        "\t-l \"logfile\"\t\tuse this option to define log file\n"\
        "\t\t\t\tdefault log output is STD\"\n"\
        "\t-o \"outputfile\"\t\tuse this option to define path to result file\n"\
        "\t-v[vv]\t\t\tuse this option to verbose log output (-v|-vv|-vvv) to define loglevel\n"\
        "\n"\
        "\t--help\t\t\tto show this page"
        print(help)
        return sys.exit(0)
    searcher = lambda x : args[args.index(x)+1] if x in args else False
    token = searcher("-t")
    host = searcher("-h")
    logfile = searcher("-l")
    outputfile = searcher("-o")
    verbose = logging.DEBUG if "-vvv" in args else logging.ERROR if "-vv" in args else logging.INFO if "-v" in args else False
    hlp = True if "--help" in args else True if len(args) <= 1 else False
    if hlp:
        return help()
    else:
        return token,host,logfile,outputfile,verbose


args = sys.argv
token,host,logfile,outputfile,verbose = menu(args)

if not verbose:
    if not logfile:
        tmplogdir = tempfile.TemporaryDirectory()
        tmplogname = os.path.join(tmplogdir.name, args[0])
        logging.basicConfig(filename=tmplogname, encoding='utf-8', level=logging.DEBUG)
    else:
        logging.basicConfig(filename=logfile, encoding='utf-8', level=logging.DEBUG)
else:
    if not logfile:
        logging.basicConfig(level=verbose)
    else:
        logging.basicConfig(filename=logfile, encoding='utf-8', level=verbose)



if host:
    root=host
else:
    root="gitlab.com"

if not token:
    token = getpass("try to define token:\t")


rest="api/v4"
projects = get_projects(token,root,rest)
allImages = {}

for project in projects:
    tmpprojdir = tempfile.TemporaryDirectory()
    if get_raw_file(token,root,rest,project["id"],payload={"ref": "master"},fname=".gitlab-ci.yml",output=tmpprojdir.name):
        logging.info("{}\n{}".format(
            project["id"],
            project["path_with_namespace"],
        ))
        jobs = []
        images = []
        pipiline_filename = os.path.join(tmpprojdir.name,".gitlab-ci.yml")

        if os.path.isfile(pipiline_filename):
            logging.info("open {}".format(pipiline_filename))
            with open(pipiline_filename, "r") as pipeline_file:
                images, jobs = get_images_from_pipeline([str(x) for x in pipeline_file.readlines()], images, jobs)

        if jobs:
            jobs = list(set(jobs))
            artifacts = []
            project_jobs = sorted(find_job(token,root,rest,project["id"],jobs), key=lambda x: x["created_at"], reverse=True)
            for job in project_jobs:
                artifacts_filename = os.path.join(tmpprojdir.name,"{}.zip".format(job["name"]+job["created_at"]))
                logging.debug(artifacts_filename)
                if job["name"] in jobs:
                    if get_artifacts(token,root,rest,project["id"],job["id"],fname=artifacts_filename) is not None:
                        jobs.remove(job["name"])
                        artifacts.append(artifacts_filename)
            for artifact in artifacts:
                try:
                    with zipfile.ZipFile(artifact, 'r') as zip:
                        member_list = [ name for name in zip.namelist() if len(re.findall(r'.*(.yaml|.yml)$', name)) > 0 ]
                        for file in member_list:
                            with zip.open(file, "r") as pipeline_file:
                                images, jobs = get_images_from_pipeline([str(x, 'utf-8') for x in pipeline_file.readlines()],images,jobs)
                except AttributeError as err:
                    logging.error(err)
                    logging.error("Corrupted zipfile")
        allImages[project["path_with_namespace"]] = list(set(images))
        logging.debug("\n")
    else:
        logging.debug("{}".format(
            project["path_with_namespace"],
        ))
        logging.debug("such no pipiline file\n")
    tmpprojdir.cleanup()

if outputfile:
    with open(outputfile, "w") as output:
            output.write(yaml.dump(allImages))
else:
    print(yaml.dump(allImages))