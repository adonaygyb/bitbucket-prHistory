from atlassian import Bitbucket
from datetime import date, datetime
import argparse
import json

def getAllPullRequests(bitbucket):
    """
    :brief: Funciton to return all pull requests user has reviewed
    :param bitbucket: Atlassian Bitbucket object instance for sending REST calls
    :return: False on failure list of PRs on success
    """
    params = {
        'role'          : 'REVIEWER',
        'limit'         : '150',
    }

    url = '/rest/api/1.0/dashboard/pull-requests'
    data = bitbucket.get(url, params=params)

    if 'values' in data:
        pr_list = (data or {}).get('values')

        while not data.get('isLastPage'):
            start = data.get('nextPageStart')
            params['start'] = start
            data = bitbucket.get(url, params=params)
            pr_list += (data or {}).get('values')

        return pr_list

    return False

def buildJsonFile(pr_list, idsid):
    """
    :brief: A function to parse pull request data and build JSON file data.
    :param pr_list: List of pull request info returned from REST call to be parsed
    :param idsid: Current reviewer idsid
    :return: Dictionary of parsed data
    """
    json_data = {}

    for pr in pr_list:

        pr_time_stamp = datetime.fromtimestamp(pr['createdDate']/1000)
        pr_month = pr_time_stamp.strftime("%B")
        pr_year = pr_time_stamp.year

        #if pr_month != curr_month:
        #    break

        pr_repo = pr['toRef']['repository']['name']
        pr_link = pr['links']['self'][0]['href']

        for reviewer in pr['reviewers']:
            if reviewer['user']['slug'] == idsid:
                if reviewer['status'] == "UNAPPROVED":
                    break
                else:
                    pr_status = reviewer['status']

                    if pr_year in json_data.keys():
                        if pr_month in json_data[pr_year].keys():
                            if pr_repo in json_data[pr_year][pr_month].keys():
                                json_data[pr_year][pr_month][pr_repo][pr_link] = pr_status
                            else:
                                json_data[pr_year][pr_month][pr_repo] = {pr_link : pr_status}
                        else:
                            json_data[pr_year][pr_month] = {pr_repo : {pr_link : pr_status}}
                    else:
                        json_data[pr_year] = {pr_month : {pr_repo : {pr_link : pr_status}}}

    return json_data

def plotMonthToPRData(pr_dict_data):
    """
    :brief: A function to plot the json data using google sheets.
    :param pr_dict_data: PR data in a dictionary format
    """
    pr_month_chartData = [["Month", "Number of Code Reviews"]]
    pr_repo_chartData = [["Repository", "Number of Code Reviews"]]
    repo_pr_counter = {}

    for year in pr_dict_data.keys():
        for month in pr_dict_data[year]:
            pr_count = 0
            for repo in pr_dict_data[year][month]:
                if repo in repo_pr_counter.keys():
                    repo_pr_counter[repo] += len(pr_dict_data[year][month][repo].values())
                else:
                    repo_pr_counter[repo] = len(pr_dict_data[year][month][repo].values())
                pr_count += len(pr_dict_data[year][month][repo].values())
            pr_month_chartData.append([month + "/" + str(year), pr_count])

    for repo_name, pr_count in zip(repo_pr_counter.keys(), repo_pr_counter.values()):
        pr_repo_chartData.append([repo_name, pr_count])

    pr_month_chart_data_str = ''
    for row in pr_month_chartData[1:]:
        pr_month_chart_data_str += "%s,\n" % row

    pr_repo_chart_data_str = ''
    for row in pr_repo_chartData[1:]:
        pr_repo_chart_data_str += "%s,\n" % row

    from string import Template

    htmlString = Template("""<html><head>    
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {packages: ['corechart']});
      google.charts.setOnLoadCallback(drawChart);

      function drawChart(){
          var pr_per_month_data = google.visualization.arrayToDataTable([$labels, $data], false);
          var pr_per_repo_data = google.visualization.arrayToDataTable([$labels2, $data2], false);

          var month_pr_chart = new google.visualization.ColumnChart(document.getElementById('month_pr_chart_div'));
          var repo_pr_chart = new google.visualization.ColumnChart(document.getElementById('repo_pr_chart_div'))
          
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

    outFileTxt = htmlString.substitute(labels=pr_month_chartData[0], data=pr_month_chart_data_str, labels2=pr_repo_chartData[0], data2=pr_repo_chart_data_str)

    with open('PrHistoryPlot.html', 'w') as f:
        f.write(outFileTxt)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Code Review Data Analytics Tool.')
    parser.add_argument('-u', '--username', default=None, help='The user\'s Bitbucket username/idsid.')
    parser.add_argument('-p', '--password', default=None, help='The user\'s Bitbucket password.')

    cmdArgs = parser.parse_args()

    usr_idsid = cmdArgs.username
    usr_passwrd = cmdArgs.password
    if not cmdArgs.username:
        usr_idsid = input("Enter idsid: ")
    if not cmdArgs.password:
        usr_passwrd = input("Enter password: ")

    curr_month = date.today().month
    bitbucket = Bitbucket(url='https://nsg-bit.intel.com:443', username=usr_idsid, password=usr_passwrd, verify_ssl=False)

    print("********************************** Beginning to Read PR Data ***********************************")
    pull_requests = getAllPullRequests(bitbucket=bitbucket)
    print("********************************** Ending to Read PR Data **************************************")
    parsed_pr_data = buildJsonFile(pr_list=pull_requests, idsid=usr_idsid)
    plotMonthToPRData(parsed_pr_data)

    with open('json_historical_data.json', 'w') as outfile:
        json.dump(parsed_pr_data, outfile)


# from requests.packages.urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)