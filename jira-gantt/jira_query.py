# from jira import JIRAError, JIRA
from jira import Issue, JIRAError
from operator import attrgetter, itemgetter
from dateutil import parser
from datetime import datetime, time

# import tempfile
import logging

DEFAULT_LOGLEVEL = 'warning'
DEFAULT_JIRA_URL = 'https://jira.example.com'
DEFAULT_OUTPUT = 'jira_export.txt'
ABSORB_LINKED_ISSUES_DEPTH = 1

JIRA_PAGE_SIZE = 50

FACTOR = 8.0 * 60 * 60

TAB = ' ' * 4

class Counter():
    def __init__(self):
        self.num = 0
    def count(self):
        prev = self.num
        self.num += 1
        return prev


# id_to_username_mapping = {}

# def to_username(value):
#     if isinstance(value, str) and len(value) >= 24:
#         if value not in id_to_username_mapping:
#             user = jirahandle.user(value)
#             id_to_username_mapping[value] = user.emailAddress.split('@')[0]
#         return id_to_username_mapping[value]
#     return value

# def set_logging_level(loglevel):
#     """Sets the logging level
#     Args:
#         loglevel (str): String representation of the loglevel
#     """
#     numeric_level = getattr(logging, loglevel.upper(), None)
#     if not isinstance(numeric_level, int):
#         raise ValueError('Invalid log level: %s' % loglevel)
#     logging.basicConfig(level=numeric_level)

def to_identifier(key):
    """Converts given key to identifier, interpretable by TaskJuggler as a task-identifier
    Args:
        key (str): Key to be converted
    Returns:
        str: Valid task-identifier based on given key
    """
    return key.replace('-', '_')



# class JiraTask():
class dataTask():

    DEFAULT_KEY = 'NOT_INITIALIZED'

    def __init__(self, issue=None):
        self.key = self.DEFAULT_KEY
        self.start = None,
        self.resolved_at_date = None
        self.properties = {}
        self.parrent = None
        self.subtasks = []
        self.start = None
        self.status = None,
        self.inward = []
        self.outward = []
        self.issue = None
        self.statuslog = []
        self._resolved_at_date = None
        self.absorbed = None


        if issue:
            self.load_from_json(issue)

    def load_from_json(self, issue):
        """Loads the object with data from a Jira issue
        Args:
            jira_issue (jira.resources.Issue): The Jira issue to load from
        """
        self.key = issue["id"]
        
        # self.dependencies = issue["dependencies"] if "dependencies" in issue.keys() else None
        self.resolved_at_date = issue["_end"] if parser.parse(issue["_end"]).strftime("%Y-%m-%d") != issue["end"] else None
        self.start =  self.start = issue["_start"] if parser.parse(issue["_start"]).strftime("%Y-%m-%d") != issue["start"] else None


class JiraTask():

    DEFAULT_KEY = 'NOT_INITIALIZED'
    MAX_SUMMARY_LENGTH = 70
    DEFAULT_SUMMARY = 'Task is not initialized'
    TEMPLATE = '''
task {id} "{description}" {{
{tab}Jira "{key}"
{props}
}}
'''

    def __init__(self, jira_issue=None):
        logging.info('Create object Task for %s', jira_issue.key)

        self.key = self.DEFAULT_KEY
        self.summary = self.DEFAULT_SUMMARY
        self.properties = {}
        self.parrent = None
        self.subtasks = []
        self.start = None
        self.status = None,
        self.inward = []
        self.outward = []
        self.issue = None
        self.statuslog = []
        self._resolved_at_date = None
        self.absorbed = None

        if jira_issue:
            self.load_from_jira_issue(jira_issue)

    def load_from_jira_issue(self, jira_issue):
        """Loads the object with data from a Jira issue
        Args:
            jira_issue (jira.resources.Issue): The Jira issue to load from
        """
        self.key = jira_issue.key
        self.issue = jira_issue
        

        self.dependencies = self.issue.fields.issuelinks

        self.start = self.issue.fields.created
        self.status = self.issue.fields.status.name,
        self.statuslog = self.collect_status_changes()
        self.subtasks = [task for task in self.issue.fields.subtasks] if "subtasks" in self.issue.fields.__dict__.keys() else []
        self.parent = self.issue.fields.parent if "parent" in self.issue.fields.__dict__.keys() else None


        summary = jira_issue.fields.summary.replace('\"', '\\\"')
        self.summary = (summary[:self.MAX_SUMMARY_LENGTH] + '...') if len(summary) > self.MAX_SUMMARY_LENGTH else summary
        if self.is_resolved:
            self.resolved_at_date = self.determine_resolved_at_date()
        self.set_absorbed()
          

    def __str__(self):
        """Converts the JugglerTask to the task juggler syntax
        Returns:
            str: String representation of the task in juggler syntax
        """
        props = "".join(map(str, self.properties.values()))
        return self.TEMPLATE.format(id=to_identifier(self.key),
                                    key=self.key,
                                    tab=TAB,
                                    description=self.summary.replace('\"', '\\\"'),
                                    props=props)


    @property
    def is_resolved(self):
        """bool: True if JIRA issue has been approved/resolved/closed; False otherwise"""
        return self.issue is not None and self.issue.fields.status.name in ('Approved', 'Resolved', 'Closed')

    @propertyimage.png
        return self._resolved_at_date

    @resolved_at_date.setter
    def resolved_at_date(self, value):
        self._resolved_at_date = value

    def collect_status_changes(self):
        changes = []
        for change in sorted(self.issue.changelog.histories, key=attrgetter('created'), reverse=True):
                # print(change.__dict__)
                for item in change.items:
                    # print(item.__dict__)
                    if item.field.lower() == 'status':
                        status = item.toString.lower()
                        prev_status = item.fromString.lower()
                        start_at = parser.isoparse(change.created)
                        changes.append({ "status":status, "created":start_at, "prev":prev_status, "end_at":None } )
        changes = sorted(changes, key=itemgetter('created'), reverse=True)
        for change in changes:
            next_change = next( ( item for item in changes if change["status"] == item["prev"] ), None )
            change["end_at"] = next_change["created"] if next_change else next_change
        return changes

    def determine_resolved_at_date(self):
        closed_at_date = None
        for change in self.statuslog:
            status = change["status"]
            if status in ('approved', 'resolved'):
                return parser.isoparse(change["created"])
            elif status in ('closed',) and closed_at_date is None:
                closed_at_date = parser.isoparse(change["created"])
        return closed_at_date

    def set_absorbed(self, absorb_status = False):
        self.absorbed = absorb_status

    def add_inward(self, key):
        self.inward.append(key)
    def add_outward(self, key):
        self.outward.append(key)

class JiraUpdateData():
    def __init__(self, handler):

        # logging.info('Tasks: %s', tasks)
        # self.tasks = self.parse_tasks(tasks) if tasks else None 
        # self.handle = JIRA(server = endpoint, token_auth = token, async_ = True, async_workers=20)
        self.handle = handler
        # self.issue_count = 0

    def parse_tasks (self, tasks):
        result = []
        for task in tasks:
            result.append(dataTask(task))

        return result
    
    def update_tasks (self, tasks):
        tasks = self.parse_tasks(tasks)
        result = []
        for task in tasks:
            busy = True
            while busy:
                try:
                    issue = self.handle.issue(task.key)
                    if task.start: issue.update(fields={"created": task.start})
                    if task.resolved_at_date: issue.update(fields={"customfield_11202": task.resolved_at_date})
                    result.append("update {} status is {}".format(task.key,"ok"))                    
                    break          
                except JIRAError as e:
                    # print(e.response.__dict__)
                    logging.error('failed to load \n"%s"', e)
                    result.append("update {} status is {} : {}".format(task.key,e.response.status_code, e.response._content)) 
                    break
                busy = True

            # issue = self.handle.issue(task.key)
            # issue.update(fields={"created":task.start, "customfield_11202": task.resolved_at_date})
            # result.append("update {} status is {}".format(task.key,"ok"))
            # res1 = self.handle.add_issue_property(issue = task.key, key = "created", data = task.start)
            # res2 = self.handle.add_issue_property(issue = task.key, key = "customfield_11202", data = task.resolved_at_date)
            # result.append("update {} statuses is {} and {} ".format(task.key,res1,res2))
        
        return result
        


class JiraQueryData():
    """Tnx melexis for usable class
        https://github.com/melexis/jira-juggler"""

    # def __init__(self, endpoint, token,  query):
    def __init__(self, handler,  query):
        """Constructs a JIRA search
        Args:
            jirahandle: JIRA client object
            query (str): The query to run
        """

        logging.info('Query: %s', query)
        self.query = query
        # self.handle = JIRA(server = endpoint, token_auth = token, async_ = True, async_workers=20)
        self.handle = handler
        self.issue_count = 0

    def load_single_issue_from_search(self, issue_key='', **kwargs):
        tasks = []
        busy = True
        query = "issuekey = \"{key}\"".format(key = issue_key)
        while busy:
            try:
                issues = self.handle.search_issues(query, maxResults=1, startAt=self.issue_count,
                                                  expand='changelog')
            except JIRAError:
                logging.error('Invalid Jira query "%s"', query)
                return None

            if len(issues) <= 0:
                busy = False

            self.issue_count += len(issues)
            for issue in issues:
                logging.debug('Retrieved %s: %s', issue.key, issue.fields.summary)
                task = JiraTask(issue)
                tasks.append(task)
        return tasks

    def load_issues_from_search(self, query=None, depend_on_preceding=False, sprint_field_name='', **kwargs):
        """Loads issues from Jira
        Args:
            depend_on_preceding (bool): True to let each task depend on the preceding task that has the same user
                allocated to it, unless it is already linked; False to not add these links
            sprint_field_name (str): Name of field to sort tasks on
        Returns:
            list: A list of Task instances
        """
        tasks = []
        busy = True
        while busy:
            try:
                if query:
                    issues = self.handle.search_issues(query, maxResults=JIRA_PAGE_SIZE, startAt=self.issue_count,
                                                  expand='changelog')
                else:
                    issues = self.handle.search_issues(self.query, maxResults=JIRA_PAGE_SIZE, startAt=self.issue_count,
                                                  expand='changelog')
            except JIRAError:
                logging.error('Invalid Jira query "%s"', self.query)
                return None

            if len(issues) <= 0:
                busy = False

            self.issue_count += len(issues)
            for issue in issues:
                logging.debug('Retrieved %s: %s', issue.key, issue.fields.summary)
                task = JiraTask(issue)
                # print(issue.fields)
                tasks.append(task)

        counter = Counter()
        while counter.count() <= ABSORB_LINKED_ISSUES_DEPTH:
            dtasks = []
            for task in tasks:
                absorbed = self.absorb_linked_issues(task)
                if absorbed:
                    dtasks += absorbed
            tasks += dtasks
            if not dtasks:
                break

        return tasks

    def absorb_linked_issues(self, task):
        result = []
        if not task.absorbed:
            task.set_absorbed(True)
            if task.issue.fields.issuelinks:
                for issuelink in task.issue.fields.issuelinks:
                    # print(issuelink.__dict__)
                    if "inwardIssue" in issuelink.raw.keys():
                        key = issuelink.raw["inwardIssue"]["key"]
                        task.add_inward(key)
                        dtasks = self.load_single_issue_from_search(issue_key = key)
                        result += dtasks
                    if "outwardIssue" in issuelink.raw.keys():
                        key = issuelink.raw["outwardIssue"]["key"]
                        task.add_outward(key)
                        # dtasks = self.load_single_issue_from_search(issue_key = key)
                        # result += dtasks
        return result

    def generate_dataframe(self, current_date = None, **kwargs):
        # TAB = "    "
        if not current_date:
            current_date = datetime.now()
        tasks = self.load_issues_from_search(**kwargs)

        data = []
        for task in tasks:
            item = {
                        "id": task.key,
                        "name": "Задача {}:\n\t{}".format(task.key, task.summary),
                        "status": task.status,
                        "start": task.start,
                        "end": task.resolved_at_date if task.resolved_at_date
                            else current_date.isoformat(),
                        # "end": parser.parse(task.issue.fields.customfield_11202).isoformat() if task.issue.fields.customfield_11202
                        #     else task.resolved_at_date if task.resolved_at_date
                        #     else current_date.isoformat(),
                        "progress": 0,
                        # "dependent_for": next((key for key in keys if key in task.outward), root)
                    }
            if task.parent:
                item["dependencies"] = str(task.parent)
            data.append(item)

        for item in data:
            item["start"] = parser.parse(item["start"]).strftime("%Y-%m-%d")
            item["end"] = parser.parse(item["end"]).strftime("%Y-%m-%d")

        return data


if __name__ == "__main__":
    print("queried")
