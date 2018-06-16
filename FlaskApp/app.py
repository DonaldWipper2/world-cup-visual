from flask import Flask, render_template, make_response
#from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import FlaskApp.sql
from flask import request, flash
import json
import requests
import csv
from datetime import date
from datetime import datetime
#https://127.0.0.1:5000/


#mysql = MySQL()
cursor = None
competitionId = 467

db = None

stages = []
teams = [] 
places = []
rounds = [] 
groups = []
games = []
standings = []
games_clear = []
space = None

teams_name_dic = {}

outGroups = [{ "name":"NATIONAL TEAMS", "color":"#ABDDA4"}, { "name":"WORLD CUP SCHEDULE", "color":"#2c7bb6"},
             { "name":"CITIES AND STADIUMS", "color":"#d7191c"}, { "name":"GROUPS ANS STAGES", "color":"#d7c119"}]


dic_sliceId = {}
dic_name2sliceId = {}
dic_sliceId2name = {}

dic_slice_2_games = {} #связь кусочка с играми

dic_games = {} #все игры для вывода

settings = {"sql_host":"us-iron-auto-dca-04-a.cleardb.net", 
            "sql_user":"b1df3776b2b56c",
            "sql_passwd":"2153543acdac76f",
            "sql_db":"heroku_0c1d0ea4e380413"
           }

app = Flask(__name__)
app.config.from_object(__name__)
app.config['TEMPLATES_AUTO_RELOAD']=True

def xstr(s):
    if s is None:
        return ''
    return str(s)

def getNormalDate(DateStr):
    return str(datetime.strptime(DateStr.strip()[0:10], '%Y-%m-%d'))[0:10]


def getConnectionBySliceId(sliceId):
    if sliceId not in dic_sliceId or sliceId not in dic_sliceId2name:
        return [-1]
    groupId = dic_sliceId[sliceId]
    if groupId == 0:
        return getAllCorellByTeamId(dic_sliceId2name[sliceId])     
    elif groupId == 1:  
        return getAllCorellByDate(dic_sliceId2name[sliceId])  
    elif groupId == 2:  
        return getAllCorellByPlace(dic_sliceId2name[sliceId]) 
    elif groupId == 3:  
        return getAllCorellByStage(dic_sliceId2name[sliceId]) 

#по команде возвращаем
#календарь, стадионы, стадии
def getAllCorellByTeamId(teamId):
    teamId = str(teamId)
    places = [g["placeId"] for g in games if g["homeTeamId"] == teamId or g["awayTeamId"] == teamId]
    dates =  [getNormalDate(g["date"]) for g in games if g["awayTeamId"] == teamId or g["homeTeamId"] == teamId ] 
    groups = ["Group" + " " + d["group_"] for d in standings if str(d["teamId"]) == teamId]
    dic_slice_2_games[dic_name2sliceId[teamId]] += [g["id"] for g in games if g["awayTeamId"] == teamId or g["homeTeamId"] == teamId]
    names = dates + groups + places
    sliceIds = []
    for name in names:
        if name in dic_name2sliceId:
            sliceIds.append(dic_name2sliceId[name])
    return sliceIds


#по дате игры возвращаем
#группы, команды, места
def getAllCorellByDate(date):
    print(date)
    places = [g["placeId"] for g in games if getNormalDate(g["date"]) == date]
    teams = [g["homeTeamId"] for g in games if getNormalDate(g["date"]) == date] + [g["awayTeamId"] for g in games if getNormalDate(g["date"]) == date]  
    groups = ["Group" + " " + d["group_"] for d in standings  if str(d["teamId"]) in teams]
    dic_slice_2_games[dic_name2sliceId[date]] += [g["id"] for g in games if getNormalDate(g["date"]) == date]
    names = teams + groups + places
    sliceIds = []
    for name in names:
        if name in dic_name2sliceId:
            sliceIds.append(dic_name2sliceId[name])
    return sliceIds

#по месту возвращаем
#группы, команды, даты
def getAllCorellByPlace(placeId):
    dates = [getNormalDate(g["date"]) for g in games if g["placeId"] == placeId]
    teams = [g["homeTeamId"] for g in games if g["placeId"] == placeId] + [g["awayTeamId"] for g in games if g["placeId"] == placeId] 
    groups =  ["Group" + " " + d["group_"] for d in standings  if  str(d["teamId"]) in teams]
    dic_slice_2_games[dic_name2sliceId[placeId]] += [g["id"] for g in games if g["placeId"] == placeId]
    names = dates + groups + teams
    sliceIds = []
    for name in names:
        if name in dic_name2sliceId:
            sliceIds.append(dic_name2sliceId[name])
    return sliceIds

#по группе возвращаем
#места, команды, даты
def getAllCorellByStage(title):
    teams = [str(d["teamId"]) for d in standings  if "Group" + " " + d["group_"] == title]
    dates = [getNormalDate(g["date"]) for g in games if g["homeTeamId"] in teams or g["awayTeamId"] in teams]
    places = [g["placeId"] for g in games if g["homeTeamId"] in teams or g["awayTeamId"] in teams]
    dic_slice_2_games[dic_name2sliceId[title]] += [g["id"] for g in games if g["placeId"] in places]
    names = dates + places + teams
    sliceIds = []
    for name in names:
        if name in dic_name2sliceId:
            sliceIds.append(dic_name2sliceId[name])
    return sliceIds




def init_data():
    global stages, games, teams, places, rounds, groups, space, standings, db 
    #initSQL()
    #settings  = read_params("settings2.json")
    #print(settings)
    db = FlaskApp.sql.database(settings['sql_host'],  settings['sql_user'],  settings['sql_passwd'], settings['sql_db'])
    standings = db.getDictFromQueryRes("standings", {"competitionId": competitionId})
    teams = [team for team in db.getDictFromQueryRes("teams_wc") if team["id"] in   [t["teamId"] for t in  standings] ]
    places = db.getDictFromQueryRes("places", {"competitionId": competitionId})  
    rounds = db.getDictFromQueryRes("rounds", {"competitionId": competitionId})
    groups = db.getDictFromQueryRes("groups", {"competitionId": competitionId})
    stages = db.getDictFromQueryRes("stages", {"competitionId": competitionId})    
    games = db.getDictFromQueryRes("games", {"competitionId": competitionId}) 
    #установим id, чтоб потом ссылаться
    i = 0
    for g in games:
        g_new = get_game_dic(g)
        g["id"] = i 
        g_new["id"] = g["id"]
        i += 1   
        games_clear.append (g_new)


def get_game_dic(g):
    game = {}
    try:
        p = [p for p in places if p["id"] == g["placeId"]][0]
        game["stadium"] = p["stadium"].split("|")[0] 
        game["city"] = p["city"]
    except:
        game["stadium"] = None 
        game["city"] = None    
    
    
    game["teamAway"] = None
    try:
        game["teamHome"] = [t for t in teams if t["id"] == g["homeTeamId"]][0]
    except:
        game["teamHome"] = None
    try:
        game["teamAway"] = [t for t in teams if t["id"] == g["awayTeamId"]][0]
    except:
        game["teamAway"] = None     
    game["status"] = g["status"]
    game["date"] = g["date"][0:10]
    game["time"] = g["date"][11:16]
    return game


def render():
    global stages, teams, places, rounds, groups, space, games, places, dic_slice_2_games
    sliceId = 0
    shares = {"teams":350, "calendar":600//3, "places":600//3, "stages":600//3}
    space  = (1000 - (shares["teams"] + shares["calendar"] +  shares["places"] + shares["stages"])) // 4

    #список команд
    for t in teams:
        t["value"] =  shares["teams"] / len(teams)
        t["color"] = "#4daa4b"
        t["sliceId"] = sliceId
        t["id_group"] = 0
        teams_name_dic[str(t["id"])] = t["name"] 
        dic_sliceId[sliceId] = 0
        dic_name2sliceId[str(t["id"])] = sliceId
        dic_sliceId2name[sliceId] = t["id"]
        sliceId += 1

    sliceId += 1 #для пространства
    #календарь игр
    for date in rounds:
        strTime =  getNormalDate(date["start_at"].strip())
        date["value"] =  shares["calendar"] / len(rounds)
        date["name"] =  strTime #strTime.strftime("%A")[0:3] + "." + strTime.strftime(" %d. %B")     
        date["color"] = "#ddea4f"
        date["sliceId"] = sliceId
        date["id_group"] = 1
        dic_sliceId[sliceId] = 1
        dic_name2sliceId[strTime] = sliceId
        dic_sliceId2name[sliceId] = strTime
        sliceId += 1
    
    sliceId += 1 #для пространства  
    #стадион + город
    for p in places:
        p["name"] = p["stadium"].split("|")[0] + " " + p["city"]
        p["value"] =  shares["places"] / len(places)
        p["color"] = "#4a69a9"
        p["sliceId"] = sliceId
        p["id_group"] = 2
        dic_sliceId[sliceId] = 2
        dic_name2sliceId[p["id"]] = sliceId
        dic_sliceId2name[sliceId] = p["id"]
        sliceId += 1
    sliceId += 1 #для пространства
    #раунды
    for s in stages:
        s["value"] =  shares["stages"] / len(stages)
        s["color"] = "#a89449"
        s["sliceId"] = sliceId
        s["id_group"] = 3
        dic_sliceId[sliceId] = 3
        dic_name2sliceId[s["title"]] = sliceId
        dic_sliceId2name[sliceId] = s["title"]
        sliceId += 1
    
    #какие игры показываем при клике
    for i in range(sliceId):
        dic_slice_2_games[i] = []
    
    click_events = []
    for curSlice in range(sliceId):
        click_events.append({"key":curSlice, "value":getConnectionBySliceId(curSlice)}) 
    
    slice_name = []
    for d in dic_slice_2_games:
        slice_name.append ( {"key":d, "value":dic_slice_2_games[d]})
    
   
    dic_slice_2_games = {}
    return render_template("world_cup2.html", teams = teams, groups = groups, rounds = rounds, places = places, stages = stages, space = space, outGroups = outGroups, click_events = click_events, games_clear = games_clear, slice_name = slice_name)




#get settings

def read_params(fn): 
    d ={} 
    try:
        with open(fn, 'r',encoding="utf-8") as file: 
            d = json.load(file) 
    except FileNotFoundError:
         print ("Error. Can't find file " + fn)
         d = {}
    return d 


    


@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        index = request.form['index']
        #del places
        resp = make_response(json.dumps({index:getConnectionBySliceId(int(index))} ))
        resp.status_code = 200
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    else:
       init_data()
    return render()
    

if __name__ == "__main__":
    app.run(debug = True)
