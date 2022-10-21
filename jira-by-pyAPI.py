# from asyncio import current_task
from audioop import reverse
from jira import JIRA, JIRAError
import argparse
from getpass import getpass as getpass
# from base64 import b64encode, b64decode
# from functools import cmp_to_key
from operator import attrgetter, itemgetter
from dateutil import parser
from datetime import datetime, time
# from natsort import natsorted, ns
# import re
import pandas as pd
# import plotly.express as px
import plotly.figure_factory as ff
from random import randrange

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

def set_logging_level(loglevel):
    """Sets the logging level
    Args:
        loglevel (str): String representation of the loglevel
    """
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)

def to_identifier(key):
    """Converts given key to identifier, interpretable by TaskJuggler as a task-identifier
    Args:
        key (str): Key to be converted
    Returns:
        str: Valid task-identifier based on given key
    """
    return key.replace('-', '_')



def calculate_weekends(date, workdays_passed, weeklymax):
    """Calculates the number of weekends between the given date and the amount of workdays to travel back in time.
    The following assumptions are made: each workday starts at 9 a.m., has no break and is 8 hours long.
    Args:
        date (datetime.datetime): Date and time specification to use as a starting point
        workdays_passed (float): Number of workdays passed since the given date
        weeklymax (float): Number of allocated workdays per week
    Returns:
        int: The number of weekends between the given date and the amount of weekdays that have passed since then
    """

    weekend_count = 0
    workday_percentage = (date - datetime.combine(date.date(), time(hour=9))).seconds / FACTOR
    date_as_weekday = date.weekday() + workday_percentage
    if date_as_weekday > weeklymax:
        date_as_weekday = weeklymax
    remaining_workdays_passed = workdays_passed - date_as_weekday
    if remaining_workdays_passed > 0:
        weekend_count += 1 + (remaining_workdays_passed // weeklymax)
    return weekend_count



# class JiraTask():
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
        logging.info('Create JugglerTask for %s', jira_issue.key)

        self.key = self.DEFAULT_KEY
        self.summary = self.DEFAULT_SUMMARY
        self.properties = {}
        self.inward = []
        self.outward = []
        self.issue = None
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
        # print(jira_issue.__dict__)
        # print(jira_issue.fields.__dict__)
        # exit()
        summary = jira_issue.fields.summary.replace('\"', '\\\"')
        self.dependencies = self.issue.fields.issuelinks
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

    @property
    def resolved_at_date(self):
        """datetime.datetime: Date and time corresponding to the last transition to the Approved/Resolved status; the
            transition to the Closed status is used as fallback; None when not resolved
        """
        return self._resolved_at_date

    @resolved_at_date.setter
    def resolved_at_date(self, value):
        self._resolved_at_date = value

    def determine_resolved_at_date(self):
        closed_at_date = None
        for change in sorted(self.issue.changelog.histories, key=attrgetter('created'), reverse=True):
            for item in change.items:
                if item.field.lower() == 'status':
                    status = item.toString.lower()
                    if status in ('approved', 'resolved'):
                        return parser.isoparse(change.created)
                    elif status in ('closed',) and closed_at_date is None:
                        closed_at_date = parser.isoparse(change.created)
        return closed_at_date

    def set_absorbed(self, absorb_status = False):
        self.absorbed = absorb_status

    def add_inward(self, key):
        self.inward.append(key)
    def add_outward(self, key):
        self.outward.append(key)

class JiraQueryData():
    """Tnx melexis for usable class
        https://github.com/melexis/jira-juggler"""

    def __init__(self, jirahandle, query):
        """Constructs a JIRA search
        Args:
            jirahandle: JIRA client object
            query (str): The query to run
        """

        logging.info('Query: %s', query)
        self.query = query
        self.handle = jirahandle
        self.issue_count = 0


    def load_issues_from_search(self, depend_on_preceding=False, sprint_field_name='', **kwargs):
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
                        dtask = JiraTask(self.handle.issue(key))
                        result.append(dtask)
                    if "outwardIssue" in issuelink.raw.keys():
                        key = issuelink.raw["outwardIssue"]["key"]
                        task.add_outward(key)
                        # dtask = JiraTask(self.handle.issue(key))
                        # result.append(dtask)
        return result


    def generate(self, output=None, **kwargs):
        """Queries JIRA and generates task-juggler output from given issues
        Args:
            list: A list of JugglerTask instances
        """
        juggler_tasks = self.load_issues_from_search(**kwargs)
        if not juggler_tasks:
            return None
        if output:
            with open(output, 'w') as out:
                for task in juggler_tasks:
                    out.write(str(task))
        else:
            for task in juggler_tasks:
                    print(str(task))
        return juggler_tasks

    def generate_dataframe(self, current_date = None, **kwargs):
        TAB = "    "
        if not current_date:
            current_date = datetime.now()
        tasks = self.load_issues_from_search(**kwargs)

        # нормальный человек описал бы тут класс или применил односвязный список
        # но я не человек я машина нахуй

        keys = [ task.key for task in tasks ]
        root = "root"

        data = [
                    {
                        "Task": task.key,
                        "status": task.issue.fields.status.name,
                        "Start": task.issue.fields.created,
                        "Finish": parser.parse(task.issue.fields.customfield_11202).isoformat() if task.issue.fields.customfield_11202
                            else task.resolved_at_date if task.resolved_at_date
                            else current_date.isoformat(),
                        "dependent_for": next((key for key in keys if key in task.outward), root)
                    } for task in tasks ]

        links_list = list( { task.key: next(( key for key in keys if key in task.outward ), root ) } for task in tasks )
        sorted_keys = []
        keys = list(set(keys))
        keys.reverse()
        while keys:
            key = keys.pop()
            llkey = next((d for d in links_list if key in d.keys()), None)
            llkey = llkey[key]            
            if llkey == root:
                sorted_keys.insert(0, key)
            elif llkey in sorted_keys:
                sorted_keys.insert(sorted_keys.index(llkey)+1, key)
            else:
                sorted_keys.append(key)

        data = [ next(d for d in data if d['Task'] == x) for x in sorted_keys]
        for key in data:
            if key["dependent_for"] != root:
                key["Task"] = "[{}]:{}".format(key["dependent_for"],key["Task"])

        return data


def main():
    argpar = argparse.ArgumentParser()
    argpar.add_argument('-e', '--endpoint', default=DEFAULT_JIRA_URL,
                        help='Link to the jira app')
    argpar.add_argument('-l', '--loglevel', default=DEFAULT_LOGLEVEL,
                        help='Level for logging (strings from logging python package)')
    argpar.add_argument('-q', '--query', required=True,
                        help='Query to perform on JIRA server')
    argpar.add_argument('-o', '--output', default=DEFAULT_OUTPUT,
                        help='Output .tjp file for task-juggler')
    argpar.add_argument('-D', '--depend-on-preceding', action='store_true',
                        help='Flag to let tasks depend on the preceding task with the same assignee')
    argpar.add_argument('-s', '--sort-on-sprint', dest='sprint_field_name', default='',
                        help='Sort unresolved tasks by using field name that stores sprint(s), e.g. customfield_10851, '
                             'in addition to the original order')
    argpar.add_argument('-w', '--weeklymax', default=5.0, type=float,
                        help='Number of allocated workdays per week used to approximate '
                             'start time of unresolved tasks with logged time')
    argpar.add_argument('-c', '--current-date', default=datetime.now(), type=parser.isoparse,
                        help='Specify the offset-naive date to use for calculation as current date. If no value is '
                             'specified, the current value of the system clock is used.')
    args = argpar.parse_args()

    set_logging_level(args.loglevel)

    token = getpass('JIRA API token:\t')
    endpoint = args.endpoint
    jirahandle = JIRA(server = endpoint, token_auth = token)

    QueryData = JiraQueryData(jirahandle, args.query)


    data = QueryData.generate_dataframe(
        depend_on_preceding=args.depend_on_preceding,
        sprint_field_name=args.sprint_field_name,
        weeklymax=args.weeklymax,
        current_date=args.current_date
    )

    # print(data)



    df = pd.DataFrame(data)

    # fig = px.timeline(df, x_start="start_date", x_end="end_date", y="key", color="status")
    # fig.update_yaxes(autorange="reversed")
    # colors = {'Not Started': 'rgb(220, 0, 0)',
    #       'Incomplete': (1, 0.9, 0.16),
    #       'Complete': 'rgb(0, 255, 100)'}
    colors = {}
    for item in data:
        if item["status"] not in colors.keys():
            red, gr, bl = randrange(0, 255, 17), randrange(0, 255, 17), randrange(0, 255, 17)
            colors.update({item["status"]: f'rgb({red},{gr},{bl})'})

    fig = ff.create_gantt(df, colors=colors, index_col='status', show_colorbar=True, group_tasks=True)
    # fig.update_yaxes(autorange="reversed")
    fig.show()
    return 0


def entrypoint():
    """Wrapper function of main"""
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()

# temp_dir = tempfile.TemporaryDirectory()
# logging.debug(print('created temporary directory', temp_dir.name))

# endpoint = 'https://jira.poidem.ru'


# # filter = jirahandle.filter('16429')

# # logging.debug(print(filter.raw))
# # logging.debug(print(jirahandle.issue('OPS-68')))

# temp_dir.cleanup()