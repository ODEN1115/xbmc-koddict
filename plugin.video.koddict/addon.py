#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import codecs
import json
import xmltodict
import sys
import os
import difflib
import xbmc
import xbmcgui
import xbmcaddon
import qrcode

def annictRecord(AnnictEpisodeID, annictToken):
    url = "https://api.annict.com/v1/me/records"
    payloads = {
        "access_token": annictToken,
        "share_twitter": "false",
        "episode_id": str(AnnictEpisodeID)
    }
    if AnnictEpisodeID != -1:
        response = requests.post(url, params=payloads)
        if int(response.status_code) != 200:
            line1 = "Error1"
            xbmcgui.Dialog().ok(__addonname__, line1)
    else:
        print("Error")
        exit()
def titleToWorkID(shortTitle, annictToken):
    url = 'https://api.annict.com/v1/works'
    payloads = {
        "access_token": annictToken,
        "per_page": "50",
        "fields": "id,title",
        "page": "1",
        "filter_title": shortTitle
    }
    response = requests.get(url, params=payloads)
    if int(response.status_code) != 200:
        line1 = "Error2"
        xbmcgui.Dialog().ok(__addonname__, line1)
    jd = json.loads(response.text.encode("utf-8"))
    DiffDict = {}
    for work in jd["works"]:
        if type(work["title"]) == unicode:
            s = difflib.SequenceMatcher(None, Title.decode("utf-8"), work["title"]).ratio()
        else:
            s = difflib.SequenceMatcher(None, Title.decode("utf-8"), work["title"].decode("utf-8")).ratio()
        DiffDict[work["title"]] = s
    AnnictWork = max(DiffDict, key=DiffDict.get)
    for work in jd["works"]:
        if AnnictWork == work["title"]:
            AnnictWorkID = int(work["id"])
    return AnnictWorkID

def workIDtoEpisodeList(AnnictWorkID, annictToken):
    AnnictEpisodeID = -1
    url = 'https://api.annict.com/v1/episodes'
    payloads = {
        "access_token": annictToken,
        "per_page": "50",
        "fields": "number,sort_number,id",
        "sort_sort_number": "asc",
        "filter_work_id": str(AnnictWorkID)
    }
    response = requests.get(url, params=payloads)
    if int(response.status_code) != 200:
        print("Error")
        exit()
    """
    1. number全部Noneでsort_numberに実際のデータ
    2. number一部Noneでsort_number % 10が実際のデータ
    とりあえずこの2つ、それ以外はエラー
    """
    AnnictEpisodeIDList = []
    jd = json.loads(response.text)
    for episode in jd["episodes"]:
        if episode["number"] is not None:
            # This is 2
            for i, episode in enumerate(jd["episodes"]):
                AnnictEpisodeIDList.append(int(episode["id"]))            
            break
        else: 
            if episode != jd["episodes"][-1]: continue
        # This is 1
        for i, episode in enumerate(jd["episodes"]):
            AnnictEpisodeIDList.append(int(episode["id"]))
    return AnnictEpisodeIDList

if __name__ == '__main__':
    AddonID ='plugin.video.koddict'
    __addon__ = xbmcaddon.Addon()
    __addonname__ = __addon__.getAddonInfo('name')
    filePath = xbmc.translatePath(os.path.join('special://home/addons/' + AddonID + "/"))
    Title = xbmc.getInfoLabel("ListItem.TVShowTitle")
    TitleShort = ""
    Number = int(xbmc.getInfoLabel("ListItem.Episode"))

    for dct in os.environ:
        xbmc.log(str(dct) + str(os.environ[dct]),level=xbmc.LOGNOTICE)

    if "ANNICT_TOKEN" in os.environ:
        annictToken = os.environ["ANNICT_TOKEN"]
    elif os.path.isfile(filePath + "ANNICT_TOKEN"):
        with open(filePath + "ANNICT_TOKEN") as f:
            annictToken = f.readline()
    else:
        line1 = "$ANNICT_TOKEN or annictToken (file) is not found."
        line2 = "Please set this environment variable. (e.g. ~/.xprofile, \"export ANNICT_TOKEN=XXXXXX\")"
        line3 = "or please put named \"annictToken\" file."
        xbmcgui.Dialog().ok(__addonname__, line1, line2, line3)
        sys.exit(1)
    for s in Title.decode("utf-8"):
        """
        表記ぶれが存在するため、
        記号もしくは空白までのタイトル一部分を検索に利用
        eg. ef- a tale of memories. -> ef のみ

        """
        if s.isalnum():
            TitleShort = TitleShort + s
        else: break
    
    TitleBase64 = Title.encode("base64")
    if TitleBase64[-1] == '\n':
        TitleBase64 = TitleBase64.rstrip()
    if os.path.exists(filePath + TitleBase64 + ".json"):
        f = codecs.open(filePath + TitleBase64 + ".json", "r", "utf-8")
        s = json.load(f)
        AnnictWorkID = int(s.keys()[0])
        if len(s[str(AnnictWorkID)]) < Number:
            print("Remake")
            """
            データが古いため、
            JSON作り直し
            """
        else:
            AnnictEpisodeID = s[str(AnnictWorkID)][Number - 1]
            annictRecord(AnnictEpisodeID, annictToken)
            line1 = "Title: " + Title
            line2 = "Episode: " + str(Number) + "_" + xbmc.getInfoLabel("ListItem.Title")
            line3 = "URI: " + "https://annict.jp/works/" + str(AnnictWorkID) + "/episodes/" + str(AnnictEpisodeID)
            #line3 = "Data was found on local filesystem."
            xbmcgui.Dialog().ok(__addonname__, line1, line2, line3)
    else:
        """
        Annict API
        作品タイトルからWorkID検索
        """
        AnnictWorkID = titleToWorkID(TitleShort, annictToken)

        """
        Annict API
        WorkIDから作品IDリスト取得
        """
        AnnictEpisodeIDList = workIDtoEpisodeList(AnnictWorkID, annictToken)

        s = {str(AnnictWorkID): AnnictEpisodeIDList}
        f = codecs.open(filePath + TitleBase64 + ".json", "w", "utf-8")
        json.dump(s, f, indent=2, ensure_ascii=False)
        f.close()

        AnnictEpisodeID = AnnictEpisodeIDList[Number - 1]
        annictRecord(AnnictEpisodeID, annictToken)

        line1 = "Title: " + Title
        line2 = "Episode: " + str(Number) + "_" + xbmc.getInfoLabel("ListItem.Title")
        line3 = "URI: " + "https://annict.jp/works/" + str(AnnictWorkID) + "/episodes/" + str(AnnictEpisodeID)
        xbmcgui.Dialog().ok(__addonname__, line1, line2, line3)
