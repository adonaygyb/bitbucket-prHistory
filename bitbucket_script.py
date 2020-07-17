from atlassian import Bitbucket
from datetime import date, datetime
from string import Template
import argparse
import json
import os

PR_DASHBOARD_PATH = '/rest/api/1.0/dashboard/pull-requests'
JSON_FILE = 'pr_data.json'
FINAL_HTML_FILE = 'final_plot.html'

class BitbucketPrPlotter(object):
    """
    :brief BitbucketPrPlotter: A class that issues GET calls to a Bitbucket server to collect number of pull-requests
        done by a user and plots that data on different charts using Google Charts JS apis.
    """

    def __init__(self):
        """
        :brief Initializer method for BitbucketPrPlotter class.
        :return:
        """
        self._user = None
        self._password = None
        self._curr_month = date.today().month
        self._url = None
        self._last_recorded_year = 0
        self._last_recorded_month = 0
        self._pr_parsed_data_dict = {}
        if os.path.isfile(JSON_FILE):
            self._read_from_json()

    def _get_month_name_or_number(self, month):
        MONTH_NUMBERS = {'January'  : 1,
                         'February' : 2,
                         'March'    : 3,
                         'April'    :4,
                         'May'      :5,
                         'June'     :6,
                         'July'     :7,
                         'August'   :8,
                         'September':9,
                         'October'  :10,
                         'November' :11,
                         'December' :12}
        MONTH_NAMES = {1: 'January',
                       2: 'February',
                       3: 'March',
                       4: 'April',
                       5: 'May',
                       6: 'June',
                       7: 'July',
                       8: 'August',
                       9: 'September',
                       10: 'October',
                       11: 'November',
                       12: 'December'}

        if isinstance(month, str):
            return MONTH_NUMBERS[month]
        elif isinstance(month, int):
            return MONTH_NAMES[month]
        else:
            raise ValueError(f"{month} is of undefined type: {type(month)}")

    def _read_from_json(self):
        """
        :brief _read_from_json: Private function to read a json file and grab the last recorded month/year
        :return:
        """
        month_num_to_name = {}
        with open(JSON_FILE) as cache_data:
            self._pr_parsed_data_dict = json.load(cache_data)
        self._last_recorded_year = max(map(lambda x: int(x), self._pr_parsed_data_dict.keys()))
        for month_name in self._pr_parsed_data_dict[str(self._last_recorded_year)].keys():
            month_num_to_name[self._get_month_name_or_number(month_name)] = month_name
        last_month_num = max(month_num_to_name.keys())
        self._last_recorded_month = last_month_num

    def _write_to_json(self, json_data):
        """
        :brief _write_to_json: Private function that writes dictionary data into a JSON file.
        :param json_data: data in a python dictionary
        :return:
        """
        with open(JSON_FILE, 'w') as outfile:
            json.dump(json_data, outfile)

    def _get_pr_per_month_data_list(self):
        """
        :brief _get_pr_per_month_data_list: Private function steps through a dictionary to count number of PRs/month.
        :return: pr_month_chartData
        """
        pr_month_chartData = [["Month", "Number of Code Reviews"]]
        for year in sorted(self._pr_parsed_data_dict.keys()):
            for month in sorted(self._pr_parsed_data_dict[year].keys(), key=self._get_month_name_or_number):
                pr_count = 0
                for repo in self._pr_parsed_data_dict[year][month]:
                    pr_count += len(self._pr_parsed_data_dict[year][month][repo].values())
                pr_month_chartData.insert(1, [f"{month}/{year}", pr_count])    # if python<3.6 => "{}/{}".format(month,year)

        return pr_month_chartData

    def _get_pr_per_repo_data_list(self):
        """
        :brief _get_pr_per_repo_data_list: Private function steps through a dictionary to count number of PRs/repo.
        :return: pr_repo_chartData
        """
        repo_pr_counter = {}
        pr_repo_chartData = [["Repository", "Number of Code Reviews"]]
        for year in self._pr_parsed_data_dict.keys():
            for month in self._pr_parsed_data_dict[year]:
                for repo in self._pr_parsed_data_dict[year][month]:
                    if repo in repo_pr_counter.keys():
                        repo_pr_counter[repo] += len(self._pr_parsed_data_dict[year][month][repo].values())
                    else:
                        repo_pr_counter[repo] = len(self._pr_parsed_data_dict[year][month][repo].values())
        for repo_name, pr_count in zip(repo_pr_counter.keys(), repo_pr_counter.values()):
            pr_repo_chartData.append([repo_name, pr_count])
        return pr_repo_chartData

    def _get_chart_data_string(self, chart_data):
        """
        :brief _get_chart_data_string: Private function concatenates a list into a string.
        :param chart_data: data in a List to be converted to str
        :return: pr_repo_chartData
        """
        ret_string = ""
        for row in chart_data[1:]:
            ret_string += f"{row},\n"   # if python<3.6 => "{},\n".format(row)
        return ret_string

    def _get_html_string(self, pr_month_chartData, pr_repo_chartData):
        """
        :brief _get_html_string: Private function to use a template html file string and insert array values.
        :param pr_month_chartData: List of PR count to month data. ["month", pr_count]
        :param pr_repo_chartData: List of PR count to repository name data. ["repo", pr_count]
        :return: html file as a string
        """
        pr_month_chart_data_str = self._get_chart_data_string(pr_month_chartData)
        pr_repo_chart_data_str = self._get_chart_data_string(pr_repo_chartData)
        htmlString = Template("""<html><head>    
                <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
                <script type="text/javascript">
                  google.charts.load('current', {packages: ['corechart']});
                  google.charts.setOnLoadCallback(drawChart);

                  function drawChart(){
                      var pr_per_month_data = google.visualization.arrayToDataTable([$labels, $data], false);
                      var pr_per_repo_data = google.visualization.arrayToDataTable([$labels2, $data2], false);

                      var month_pr_chart = new google.visualization.ColumnChart(document.getElementById('month_pr_chart_div'));
                      var repo_pr_chart = new google.visualization.PieChart(document.getElementById('repo_pr_chart_div'))

                      month_pr_chart.draw(pr_per_month_data);
                      repo_pr_chart.draw(pr_per_repo_data);
                  }
                </script>
                </head>
                <body>
                <div style='text-align:center; font-size:20px'>
                    <h1>Code Review History Dashboard</h1>
                </div>
                <div id = 'month_pr_chart_div' style='width:800px; height:600px; float:left;'></div>
                <div id = 'repo_pr_chart_div' style="margin-left: 800px; height:600px"></div>
                </body>
                </html>""")
        return htmlString.substitute(labels=pr_month_chartData[0], data=pr_month_chart_data_str,
                                     labels2=pr_repo_chartData[0], data2=pr_repo_chart_data_str)

    def _is_pr_cached(self, pr):
        """
        :brief _is_pr_cached: A flag for checking if current PR information is already cached.
        :param pr: data of a single pull request entry the user is reviewing.
        :return: boolean
        """
        returnVal = False
        if self._last_recorded_year and self._last_recorded_month:
            pr_time_stamp = datetime.fromtimestamp(pr['createdDate'] / 1000)
            pr_month = int(pr_time_stamp.strftime("%m"))
            pr_year = int(pr_time_stamp.year)

            # 2019 < 2020 (True); 06-2020 <= 08-2020 (True); 06-2020 > 80-2019 (False)
            if (pr_year < self._last_recorded_year):
                returnVal = True
            elif pr_month < self._last_recorded_month:
                if (pr_year <= self._last_recorded_year):
                    returnVal = True
        return returnVal

    def _write_to_html(self, outFileTxt):
        """
        :brief _write_to_html: Private function for writing a string to an html file.
        :param outFileTxt: string to be written to .html file
        :return:
        """
        with open(FINAL_HTML_FILE, 'w') as f:
            f.write(outFileTxt)

    def get_raw_pull_request_data(self):
        """
        :brief get_raw_pull_request_data: A function to return all pull requests user has reviewed from server
        :return: A list of raw pull-request data values.
        """
        bitbucket = Bitbucket(url=self._url, username=self._user, password=self._password, verify_ssl=False)
        params = {
            'role'          : 'REVIEWER',
            'limit'         : '150',
        }
        print("****************************** Beginning to Read Pull Request Data ******************************")
        data = bitbucket.get(PR_DASHBOARD_PATH, params=params)
        pr_data_list = []
        if 'values' in data:
            pr_data_list = (data or {}).get('values')

            # Check if last page or the oldest pr entry is saved somewhere before reading another page
            while not data.get('isLastPage') and not self._is_pr_cached(pr_data_list[-1]):
                start = data.get('nextPageStart')
                params['start'] = start
                data = bitbucket.get(PR_DASHBOARD_PATH, params=params)
                pr_data_list += (data or {}).get('values')
        print("******************************* Ending to Read Pull Request Data *********************************")
        return pr_data_list

    def parse_and_cache_pr_data(self, pull_requests):
        """
        :brief parse_and_cache_pr_data: - A function to parse raw pull request data and cache values in JSON file.
        :return:
        """
        for pr in pull_requests:
            pr_time_stamp = datetime.fromtimestamp(pr['createdDate']/1000)
            pr_month_name = pr_time_stamp.strftime("%B")
            pr_year = str(pr_time_stamp.year)
            # skip parsing if there is cached data for this pr already.
            if self._is_pr_cached(pr):
                continue
            pr_repo = pr['toRef']['repository']['name']
            pr_link = pr['links']['self'][0]['href']
            for reviewer in pr['reviewers']:
                if reviewer['user']['slug'] == self._user:
                    if reviewer['status'] == "UNAPPROVED":
                        break
                    else:
                        pr_status = reviewer['status']
                        if pr_year in self._pr_parsed_data_dict.keys():
                            if pr_month_name in self._pr_parsed_data_dict[pr_year].keys():
                                if pr_repo in self._pr_parsed_data_dict[pr_year][pr_month_name].keys():
                                    self._pr_parsed_data_dict[pr_year][pr_month_name][pr_repo][pr_link] = pr_status
                                else:
                                    self._pr_parsed_data_dict[pr_year][pr_month_name][pr_repo] = {pr_link : pr_status}
                            else:
                                self._pr_parsed_data_dict[pr_year][pr_month_name] = {pr_repo : {pr_link : pr_status}}
                        else:
                            self._pr_parsed_data_dict[pr_year] = {pr_month_name : {pr_repo : {pr_link : pr_status}}}
        self._write_to_json(self._pr_parsed_data_dict)

    def plot_data(self):
        """
        :brief plot_data: A function to write the parsed pr data into an html file to be plotted.
        :return:
        """
        pr_month_chartData = self._get_pr_per_month_data_list()
        pr_repo_chartData = self._get_pr_per_repo_data_list()
        html_formatted_file = self._get_html_string(pr_month_chartData, pr_repo_chartData)
        self._write_to_html(html_formatted_file)

    def prompt_user(self, user, password, url):
        """
        :brief prompt_user: A function check the presence of username and password and prompt user for input if None.
        :param user: Username received from Argparse/cmd line
        :param password: Password received from Argparse/cmd line
        :param url: Bitbucket server URL received from Argparse/cmd line
        :return:
        """
        if user:
            self._user = user
        else:
            self._user = input("Enter idsid: ")
        if password:
            self._password = password
        else:
            self._password = input("Enter password: ")
        if url:
            self._url = url
        else:
            self._url = input("Enter the Bitbucket server URL: ")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Code Review Data Analytics Tool.')
    parser.add_argument('-us', '--username', default=None, help='The user\'s Bitbucket username/idsid.')
    parser.add_argument('-ps', '--password', default=None, help='The user\'s Bitbucket password.')
    parser.add_argument('-ur', '--url', default=None, help='The Bitbucket server link(url).')

    cmdArgs = parser.parse_args()

    plotter = BitbucketPrPlotter()
    plotter.prompt_user(cmdArgs.username, cmdArgs.password, cmdArgs.url)
    pr_list = plotter.get_raw_pull_request_data()
    plotter.parse_and_cache_pr_data(pr_list)
    plotter.plot_data()

    #bitbucket = Bitbucket(url='https://nsg-bit.intel.com:443', username=usr_idsid, password=usr_passwrd, verify_ssl=False)



# from requests.packages.urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)