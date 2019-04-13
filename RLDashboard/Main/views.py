from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from .forms import NameForm
from django.template.loader import render_to_string
import re
import json
import csv

def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200 
            and content_type is not None 
            and content_type.find('html') > -1)


def log_error(e):
    """
    It is always a good idea to log errors. 
    This function just prints them, but you can
    make it do anything.
    """
    print(e)

# Create your views here.
def index(request):
    data = ""
    link = ""
    playerName = "-1"
    if request.method == 'POST':
        form = NameForm(request.POST)
        if form.is_valid():
            playerName = form.cleaned_data['your_name']
    else:
        form = NameForm()
       

    return render(
            request,
            "Main/index.html",  # Relative path from the 'templates' folder to the template file
            # "index.html", # Use this code for VS 2017 15.7 and earlier
            {
                'title' : "Lookup",
                'content' : data,
                'form': form,
                'link': link,
                'playerName': playerName,
            }
        )

def checkreplay(request):
     raw_html = (simple_get('https://ballchasing.com/?title=&player-name='+ request.GET['playerName'] +'&size=&ranked=&season=0&replay-after=&replay-before=&upload-after=&upload-before='))
     html = BeautifulSoup(raw_html, 'html.parser')
     for links in html.findAll('a', href=re.compile('^/replay/')):
         link = links["href"]
         break
     return HttpResponse(link)

def checkreplayCalc(request):
     raw_html = (simple_get('https://calculated.gg/players/' + request.GET['playerName'] + '/overview'))
     html = BeautifulSoup(raw_html, 'html.parser')
     for links in html.findAll('a', href=re.compile('^/replays/')):
         link = links["href"]
         break
     return HttpResponse(link[9])

def getreplayCalc(request):
    with open('https://calculated.gg/api/replay/' + request.GET['replay'] + '/basic_player_stats/download') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row.update({fieldname: value.strip() for (fieldname, value) in row.items()})
            totalMove = row["timeatboostspeed"] + row["timeatslowspeed"] + row["timeatsupersonic"]
            row["bs%"] = row["timeatboostspeed"] / totalMove
            row["ss%"] = row["timeatsupersonic"] / totalMove
            row["bl%"] = row["timeatslowspeed"] / totalMove
        html = render_to_string("Main/replaystats.html",{'content': reader})
        return HttpResponse(html)

def getreplay(request):
    raw_html = (simple_get('https://ballchasing.com' + request.GET['replay'] + '/stats#movement'))
    html = BeautifulSoup(raw_html, 'html.parser')
    raw_html = raw_html.decode("utf-8") 
    start = raw_html.find("window.bcStats.Create")
    raw_html = raw_html[start + 22:]
    end = raw_html.find("}]});")
    raw_html = raw_html[:end + 3]
    data = json.loads(raw_html)
    playerColor = "orange"
    enemyColor = "blue"
    for val in data["blue"]["players"]:
        if val["name"].lower() == request.GET['playerName'].lower():
            playerColor = "blue"
            enemyColor="orange"
            break
    stats =  data[playerColor]["players"] + data[enemyColor]["players"]
    yourSize = len(data[playerColor]["players"])
    theirSize = len(data[playerColor]["players"])
    yourScore = data[playerColor]["goals"]
    theirScore = data[enemyColor]["goals"]
    if yourScore > theirScore:
        resultColor = "DivResultWin"
    else:
        resultColor = "DivResultLose"
    html = render_to_string("Main/replaystats.html",{'content': stats,'YourScore':yourScore,'TheirScore':theirScore,'YourSize':yourSize,'TheirSize':theirSize,'ResultColor':resultColor})
    return HttpResponse(html)