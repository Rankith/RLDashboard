from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from .forms import NameForm
from django.template.loader import render_to_string
import pickle
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import re
import json
import csv
import datetime

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
    #try:
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
        EnterToSheet(stats,yourScore,theirScore,yourSize,playerColor,request.GET['replay'])
        return HttpResponse(html)
    #except:
        html = ""

def EnterToSheet(data,yourScore,theirScore,yourSize,playerColor,replayID):
    dothis = True
    if dothis:
        scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
        #creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
        ServiceAccountCredentials.from_json({
  "type": "service_account",
  "project_id": "rldashboard",
  "private_key_id": "961ab931b49d636a2d9c217aa6f0798a1b9912f6",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDBC58mxKaNiq79\nPLCjpV65WjXPV9YwrcIHP5+l0NsZIvej1h4NbC9n9w6eWQKODKeXRx6DtTxyLx5F\nTDgEg/KAc+v5jYmqN9HykemLH6gf0USaDMKB0S7d8OjrwbPtxoFRzQiP4ZxHSj7F\nMNfhB908UGezVvRwH8ZalxQmoEQ3Ci8tgf29ZbrmjTQGGln4Buob/CpbWikRbAjJ\nIwohjJdqGz0fv9kfVAuMFVFHQcw4IvJvfZDLUiItqFb7+2+Lb3MUZ7rM2aQL8+Gw\nXwARMvKblBZq6TkYqdKp2lco7n3rKJ711oYuir/6XvJf2LXd7cgQiuB8judRTWJI\ngQpJ+NJZAgMBAAECggEAFIfh40Oi2wbW2YPs3VqnGltnwad71i2EpzSzC/WMd73q\nTHhnNdI9sHbsDRc2WFksMcCUlDlgNlyggYo7ou9NiS/K9v2AmKPbJksyZWN2g/vD\nqgaVYS0YKO6INxqgwjcMZeDCelrqPgK9bkdljj9B3jpG7SHgWVRnyharQ/hjiN7S\nu3FSVK9xORKorUVkn+zRRCjpA28ldak/cW5E46G7qMxyHIFiD0gxkM8Z1rcPdknd\nO31um8cFxSY4TTzew72mfOUsTc6+mZZB8LXvmpLIA8H8CQTXALepIEt/Sb4qDS5g\nMNT8wozI9Uxm0tVydox8C3ZJx7aCjA/HktWwqvSZyQKBgQD88CUPhnZWKflTb5ey\n39cVtDscEx6hXjK2Z4K+MuVbsep/48tJRz7JOT7IJCLUDhH0Qf7+vhReCteVRa/T\ntN2+uA4N6PMV1+XD4ytmKSYm5sLf2WUA3SOGqxPwWQBUmNqeCG4tLscEVmlqVCm3\nprblcwoEJl3yGF+Yc6BKBF2YzwKBgQDDYd6Xdfhb1E8OgGWkCMf9gXU0UhHrkqf7\nYe45NESt2mr1LIw7Mkeesk77hH4p/hcItLShuiyX+0ur6kKllelB95QtVOnYmpIQ\nUsCOD6EonEhLr/gilCnkkYVCjVMGvzoL1AV9FXOJBmp4uJfOZRc0AiDOTmTiB2gJ\nDllQOajcVwKBgQC+dQUy/4izsL9wuCJ+KlaGnUO1DCCQWaHN/3tPRHu34+wziI9W\nCjOYyWYgxjUDf+S9C8S6hN5JQdi7KdIPk601ItpSVwpTdFIqgi/3qRx1RmWOsN+B\nGwLZMJC+9gVtrftP7AEqPILXHUobKmyPQRWPCGSOY2VyGjBBVy9nDIp9uQKBgDgu\ng1AwNvtI4Ha+CvwRHljSCf7Cfq6rnCwX6+V9FyaawNjBN42qFpgWk8mVPqYaj0sM\nk0hR/ZKySv8jPIjaw5kZdP1YBmongEq7UO1Ip0HDNrK05fgjfKxh/9y0QKSXBjzy\neaWPLoq/UoxmIBjUTsjAt+g6+J1aHdtEyf/cpKa/AoGAFogDm3MPp2eA6EyD1m67\n7TPUwv5XMtlP97wx1ZdwButiGPjaSe3uayNxq8J5R4Kn+/sAQ2iBE1muH8GF1Twr\nA0EmqT9Ohp0OJ8t0r2qKBMezVW+3/VIq4o4UONuLT05WKaOMFVyU4FFXp458SkNG\nZ9WnvmQQul9em3qBY//4X5o=\n-----END PRIVATE KEY-----\n",
  "client_email": "main-843@rldashboard.iam.gserviceaccount.com",
  "client_id": "104102762953073532514",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/main-843%40rldashboard.iam.gserviceaccount.com"
}
)
        client = gspread.authorize(creds)

        StatsSheet = client.open("RLStats").worksheet("StatsDump")
        GamesSheet = client.open("RLStats").worksheet("S10")

        replayID = "https://ballchasing.com" + replayID

        if not replayID in GamesSheet.col_values(12):

            if yourScore > theirScore:
                WL = "W"
            else:
                WL = "L"
       
            if yourSize == 3:
                size = "3v3"
            elif yourSize == 2:
                size = "2v2"
            else:
                size = "1v1"

            currentDT = datetime.datetime.now()
            formattedDT = currentDT.strftime("%m/%d/%Y %H:%M:%S")
            if formattedDT[0:1] == "0":
                formattedDT = formattedDT[1:]

            Sylv,Sam,Chris,Tranx = "","","",""
            numP = 0
            for i in range(len(data)):
                if data[i]["name"].lower() == "sylv":
                   Sylv = "Julian"
                   numP += 1
                elif data[i]["name"].lower() == "bishopxi":
                   Chris = "Chris"
                   numP += 1
                elif data[i]["name"].lower() == "workaholic":
                   Sam = "Sam"
                   numP += 1
                elif data[i]["name"].lower() == "tranxrl":
                   Tranx = "Tranx"
                   numP += 1
            if numP >= 2:
                GamesSheet.insert_row([WL,yourScore,theirScore,'',size,'',Chris,Sylv,Sam,Tranx,'',replayID],10)
                GamesSheet.update_cell(10,6,formattedDT)

                #now do stat sheet
                for i in range(len(data) - 1,-1,-1):
                    if i == yourSize - 1:
                        #opponent header
                        StatsSheet.insert_row([theirScore,'Them'],1)
                    statLine = ['']
                    for j,k in data[i].items():
                        statLine.append(k)
                    StatsSheet.insert_row(statLine,1)
                    #StatsSheet.insert_row(['',data[i]["name"],data[i]["goals"],data[i]["assists"],data[i]["saves"],data[i]["shots"],data[i]["avg_speed"],data[i]["percent_supersonic_speed"],data[i]["percent_boost_speed"],data[i]["percent_slow_speed"],data[i]["amount_collected"],data[i]["count_collected_big"],data[i]["count_collected_small"],data[i]["time_zero_boost"],data[i]["count_powerslide"],data[i]["avg_powerslide_duration"],data[i]["avg_distance_to_ball"],data[i]["time_behind_ball"],data[i]["time_infront_ball"]],1)
                StatsSheet.insert_row([yourScore,'Us'],1)
                statLine = ['']
                for j,k in data[0].items():
                    statLine.append(j)
                StatsSheet.insert_row(statLine,1)
                #StatsSheet.insert_row([yourScore,'You','G','A','Sa','Sh','Speed','%SS','%BS','%SL','Boost Col.','Big','Small','0 Boost','PS Num','PS Avg','Dist','Behind B','Front B'],1)
                StatsSheet.insert_row([replayID],1)
                StatsSheet.insert_row([''],1)
               # GamesSheet.update_cell(9,2,yourScore)
               # GamesSheet.update_cell(9,3,theirScore)