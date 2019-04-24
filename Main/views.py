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
import os
from django.conf import settings

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

        try:
            if settings.DEBUG == False:
                print("Getting Creds")
                keytest = os.environ['GKey']
                #keytest = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDyzC1e3dDKoSmI\nQetIlbBbugBodsiDt5RDUSdF30fWNDf9XtLQV5Y7LQ/uFAQm4E1t+FZpnuPV0qam\nETs2i2S0w6q9xsH+rj+Oo5XD1mdGXEB8otsNAWuX3tzTkxRneXMB/Er7ydlXhNXD\nZUgHDDCJr+gwps7nBd78oM1rBuKFjfXFSoxmPFr5RqZO9qHemEFV47Oooobd3WrE\nF0jChIR+gmQ2i9rBW9tn+2VXyxHYSudeE2PE1Y0aa+B907BzkDrbtrImSjM2lHCf\nR5Mn+taFts3t1p+cg55O3DnnP4CEM7HHVymN60xt3V/3JMWu04kjP+SqK+tCTU8c\nqWmR/YRbAgMBAAECggEAHkq0BGh3QridtmbHBIzMbn1DzMS5GpneURHAbRrA2ywz\nqhRZB+5Ni3+BQ8pShEkqz+QSX+YXdddsvD5dHV6Bx328ASZZkL1Lp6+oIUFQLDqZ\nPxOQccxyEIYZFfp9KrW/0Akaj9RsndswUksCFAME0UDVnrBJExCr8+faCRbYTyIb\nQ8nSPKTQrr6XbEL5NuOoRq264y/Kb3lCxbuKr27BbsSjyA86XT7a/V42YRVmmvB0\nODjlbt/X7j8ruoadurkIxV01sU5onvCibk4S2NoGrw+ZC0SLV8HELANvsvisqiDb\n+5ho72g8AB8YAzdw94ex9JjHLlPD3EELATdsnWlQ0QKBgQD/aBjC2UtnuVDmlcVs\n8rFt+nxzRiZ8pKD2h2qQSbUzHIQ19PT+jKSOCz+kM9bL6/IpkGzXJ8GDP+FQyowP\nBCj6MIo7SeqcPgEcXcyxouzsX0no9Hvasuem9d/4Qu+wJa+jMLnkDC0dXT4D+MVt\n1fl+n5CsKzLaaxMczLZG0yRDKwKBgQDzXJTNTwqNCfloJ/OvUEh5VRwnexaIFBTj\nGm2ekHc/zUmSYH3Ap5Uu9DeDG4n06mNRp9tQ7gEGNA0bIT4iy1muJQOioXI8lgGK\nrFKYymyHsgpEXKImmoTIsCWb+M3ASE0bFQdcpmqXUEVvXUWt8slOhkqdixNcE4Qs\nEtob+OHrkQKBgCY4HpRxzc3ctlV7DgsKmjB57kuVsMawIAIkK3ciAIKAfuxQFqVM\nyIcU+dYJh9gGG7vKh+7+XP/V/FKJrMHGfpdJ0jWjDv+Ia8Qh6TKfzdJlQ/sfMrV8\nVhvu6TAOXC3AxfKmpPqSM+IUBOa1QF36ShZ/rDeHU1nJ8hc6LwCUMfX3AoGBAOIM\nzh9C2y8U47lO2viuXxNs7iDyIYS2+ovVAZu23z3BZyRzQnvQbi9WI7ZBv0xi52xy\nubIb0ZG8iav4nend72hl81F+G0mRoM75sCNCa7tDsmu7i9bF0q9DhzuwyRVhU1Xj\nm5oA7qOsqUJ/Zfjkuv6YmPhrtcjiS/RQco5nCRsxAoGAYps5PwJ0gJ+n5O5RbJA0\nf1xChZmM3nf9ghdP2mN/HPT3SNwbNXiO9fnHNlixZzJreJZko45l86Pqk3NqTPft\nc6fsNkeTGYZWpN/MpYGdanEVBvjjgxP0sfHbvkGsECXHLUQfrcrBkl5j8fQJM65G\neSEsnL/6GbDGm0WOnePAWH4=\n-----END PRIVATE KEY-----\n"
                creds = ServiceAccountCredentials.from_json_keyfile_dict({
                  "type": "service_account",
                  "project_id": "rldashboard",
                  "private_key_id": "d0db21f447ea1452fc822e0f4372a99e6caf235d",
                  "private_key": keytest,
                  "client_email": "main-843@rldashboard.iam.gserviceaccount.com",
                  "client_id": "104102762953073532514",
                  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                  "token_uri": "https://oauth2.googleapis.com/token",
                  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/main-843%40rldashboard.iam.gserviceaccount.com"
                }
                , scope)
            else:
                 creds = ServiceAccountCredentials.from_json_keyfile_name("client_secret.json",scope)
            print(creds.serialization_data['private_key'])
            print("Got Creds")
            client = gspread.authorize(creds)
            print("Authorized Creds")
            StatsSheet = client.open("RLStats").worksheet("StatsDump")
            GamesSheet = client.open("RLStats").worksheet("S10")
            print("Got Sheets")
        except Exception as e: print(e)
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
            if numP >= 1:
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