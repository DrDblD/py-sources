
# from genericpath import exists
from asyncio.log import logger
import time
import requests
from getpass import getpass
# from git import Repo
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


def paginated_get(url=str(),headers=dict(),params=dict(),exit_query=None):
    output = []
    params["per_page"] = 50
    r = requests.get(url=url, headers=headers,params=params)
    r.raise_for_status()
    output += r.json()
    next_page=int(r.headers["x-next-page"])
    # print(r.headers["x-total-pages"])
    for i in range(next_page, int(r.headers["x-total-pages"])):
        if exit_query is not None:
            if exit_query(output):
                logging.debug("exit query break")
                # logging.debug(output)
                break
        params["page"]=next_page
        req = requests.get(url=url, headers=headers, params=params)
        output += req.json()
        next_page=req.headers["x-next-page"]
        # print(next_page)
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
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
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
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
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
    # logging.debug(pipefile)
    
    pipetext = "".join(pipefile)
    pipeline = yaml.safe_load(pipetext)
    # print(pipeline)
    image_keys = deepFindAll(pipeline, "image")
    # logger.debug("images")
    # logger.debug(image_keys)
    trigger_keys = deepFindAll(pipeline, "trigger")
    if trigger_keys:
        for key in trigger_keys:
            includes = deepFindAll(key, "include")
            if includes:
                for include in includes:
                    # logger.debug("trigger jobs")
                    # logger.debug(includes)
                    jobs.append(include["job"])
    output = []
    if image_keys:
        for key in image_keys:
            if type(key)==type({}):
                output.append(key["name"])
            else:
                output.append(key)
    for image in output:
        logger.info(image)
    images += output
    # print(re.findall(r'(.*)$', line))
    # i_matches = re.findall(r'image:\s(.*)', line)
    # in_matches = re.findall(r'image:\s*$^\s*(.*)', line)
    # tr_matches = re.findall(r'(trigger:)', line)
    # job_matches = re.findall(r'job:\s(.*)', line)
    # needs_matches = re.findall(r'needs:\s*$^\s*-\s(.*)$', line, flags=re.MULTILINE)
    # if len(i_matches) > 0:
    #     logging.debug("image: {}".format(i_matches[0]))
    #     images.append(i_matches[0])
    # if len(tr_matches) > 0 and len(needs_matches) > 0:
    #         logging.debug("trigger:needs: {}".format(needs_matches[0]))
    #         jobs.append(needs_matches[0])
    # if len(job_matches) > 0:
    #     logging.debug("job:".format(job_matches[0]))
    #     jobs.append(job_matches[0])
    # logging.debug(jobs)
    return images, jobs

# groups = get_groups(token,root,rest)
# print(groups)
# for group in groups:
#    projects = get_group_projects(token,root,rest,group["id"])

# projects = [project  for project in get_group_projects(token,root,rest,group["id"])]
# for project in projects:
#     print(project)
# import json
# print(json.dumps(projects, indent=4, sort_keys=True))

tmplogdir = tempfile.TemporaryDirectory()
# if os.path.exists('gitlab-search-package.py.log'): os.remove('gitlab-search-package.py.log')
tmplogname = os.path.join(tmplogdir.name, 'gitlab-search-package.py.log')
logging.basicConfig(filename=tmplogname, encoding='utf-8', level=logging.DEBUG)
rest="api/v4"
root="gitlab.poidem.ru"
# token=getpass() #token
token="glpat-Uh8zoJGrwBJyiFAQwLgC"

print(sys.argv)

projects = get_projects(token,root,rest)
images = []

for project in projects:
    tmpprojdir = tempfile.TemporaryDirectory()
    
    # repo = Repo.clone_from(project["ssh_url_to_repo"], tmpprojdir.name)
    # with repo.git.custom_environment(GIT_SSH_COMMAND='ssh -i ~/.ssh/gituser'):
    #     repo.remotes.origin.fetch()
    #     repo.heads.master.checkout()
    #     repo.remotes.origin.pull()

    if get_raw_file(token,root,rest,project["id"],payload={"ref": "master"},fname=".gitlab-ci.yml",output=tmpprojdir.name):
        logging.info("{}\n{}".format(
            project["id"],
            project["path_with_namespace"],
        ))
        jobs = []
        pipiline_filename = os.path.join(tmpprojdir.name,".gitlab-ci.yml")

        if os.path.isfile(pipiline_filename):
            logging.info("open {}".format(pipiline_filename))
            with open(pipiline_filename, "r") as pipeline_file:
                images, jobs = get_images_from_pipeline([str(x) for x in pipeline_file.readlines()], images, jobs)
        # else:
        #     print(tmpprojdir.name)
        #     for rots, dirs, files in os.walk(tmpprojdir.name):
        #         for file in files:
        #             print(file)

        if jobs:
            jobs = list(set(jobs))
            logging.debug(jobs)
            artifacts = []
            project_jobs = sorted(find_job(token,root,rest,project["id"],jobs), key=lambda x: x["created_at"], reverse=True)
            for job in project_jobs:
                artifacts_filename = os.path.join(tmpprojdir.name,"{}.zip".format(job["name"]+job["created_at"]))
                logging.debug(artifacts_filename)
                if job["name"] in jobs:
                    if get_artifacts(token,root,rest,project["id"],job["id"],fname=artifacts_filename) is not None:
                        jobs.remove(job["name"])
                        logging.debug(jobs)
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
        logging.debug("\n")
    else:
        logging.debug("{}".format(
            project["path_with_namespace"],
        ))
        logging.debug("such no pipiline file\n")
    tmpprojdir.cleanup()
images = list(set(images))
logging.debug(images)

with open("images.txt", "w") as output:
    for image in images:
        output.write("\n")
        output.write(image)

tmplogdir.cleanup()
