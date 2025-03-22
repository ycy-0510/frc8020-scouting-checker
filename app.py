import datetime
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import json
import requests

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Auto:
    def __init__(self, leave, coral):
        self.leave = leave
        self.coral = coral


class Match:
    def __init__(self, position, auto):
        self.position = position
        self.auto = auto


class CommentData:
    def __init__(self, comments, matchNumber, name=""):
        self.name = name
        self.comments = comments
        self.matchNumber = matchNumber


if not firebase_admin._apps:
    firebase_json = st.secrets["firebase"]["json_credentials"]
    # Parse the JSON string into a Python dictionary
    credentials_dict = json.loads(firebase_json)
    # Initialize Firebase Admin SDK using the parsed credentials
    cred = credentials.Certificate(credentials_dict)
    firebase_admin.initialize_app(cred)
db = firestore.client()

st.set_page_config(page_title="FRC#8020 Scouting Checker", layout="centered")
st.title("FRC#8020 Scouting Checker")

user = st.text_input("Enter User Name: ")
serialCode = st.text_input("Enter Serial Code: ",type="password")
if  user in st.secrets["serial"] and serialCode == st.secrets["serial"][user]:
    tba_api_key = st.secrets["tba"]["API"]

    # Construct the API URL
    api_url = f"https://www.thebluealliance.com/api/v3/event/2025casd/matches"
    headers = {"X-TBA-Auth-Key": tba_api_key}

    # get match results from TBA
    matchResultRes = requests.get(api_url, headers=headers)
    matchResultRes.raise_for_status()  # Raise an exception for bad status codes
    matchResults = matchResultRes.json()
    #sort match by mac number
    matchResults.sort(key=lambda x: x['match_number'])
    ##show win/loss and score
    st.sidebar.markdown("### Match Results")
    for matchResult in matchResults:
        st.sidebar.markdown(f"### Match {matchResult['match_number']}")
        st.sidebar.markdown(f'''
                    ||1|2|3|Score|
                    |---|---|---|---|---|
                    |Blue|{matchResult['alliances']['blue']['team_keys'][0].replace('frc','')}|{matchResult['alliances']['blue']['team_keys'][1].replace('frc','')}|{matchResult['alliances']['blue']['team_keys'][2].replace('frc','')}|{matchResult['alliances']['blue']['score']}|
                    |Red|{matchResult['alliances']['red']['team_keys'][0].replace('frc','')}|{matchResult['alliances']['red']['team_keys'][1].replace('frc','')}|{matchResult['alliances']['red']['team_keys'][2].replace('frc','')}|{matchResult['alliances']['red']['score']}|''')
        st.sidebar.markdown(f"{matchResult['winning_alliance']} Alliance Wins")
        if matchResult['actual_time'] != None:
            st.sidebar.markdown(f"Time: {datetime.datetime.fromtimestamp(matchResult['actual_time'])}")
            if matchResult['score_breakdown'] != None:
                st.sidebar.markdown(f"### Score Breakdown")
                st.sidebar.markdown(f"Blue Alliance:")
                st.sidebar.markdown(f"Total Points: {matchResult['score_breakdown']['blue']['totalPoints']}")
                st.sidebar.markdown(f"RP: {matchResult['score_breakdown']['blue']['rp']}(+{1 if matchResult['score_breakdown']['blue']['autoBonusAchieved'] else 0}+{1 if matchResult['score_breakdown']['blue']['coralBonusAchieved'] else 0}+{1 if matchResult['score_breakdown']['blue']['bargeBonusAchieved'] else 0})")
                st.sidebar.markdown(f"Red Alliance:")
                st.sidebar.markdown(f"Total Points: {matchResult['score_breakdown']['red']['totalPoints']}")
                st.sidebar.markdown(f"RP: {matchResult['score_breakdown']['red']['rp']}(+{1 if matchResult['score_breakdown']['red']['autoBonusAchieved'] else 0}+{1 if matchResult['score_breakdown']['red']['coralBonusAchieved'] else 0}+{1 if matchResult['score_breakdown']['red']['bargeBonusAchieved'] else 0})")
                st.sidebar.markdown("Coopertition" if matchResult['score_breakdown']['blue']['coopertitionCriteriaMet'] else "")
                #score_breakdown/videos
            if len(matchResult['videos']) > 0:
                st.sidebar.link_button("Watch Video", f"https://www.youtube.com/watch?v={matchResult['videos'][0]['key']}")
        else:
            st.sidebar.markdown(f"Time*: {datetime.datetime.fromtimestamp(matchResult['time'])}")
        # st.sidebar.markdown(matchResult)


    ##==================Scouting Checker==================
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes

    matches = response.json()
    #sort match by mac number
    matches.sort(key=lambda x: x['match_number'])
    # Parse the response and extract the relevant information
    matchNumbers = [match["match_number"] for match in matches]
    selectMatch = st.selectbox("Select Match Number: ", matchNumbers)
    scouterNames = st.text_input("Enter Scouter Name: ")
    scouterNameList = scouterNames.split()
    while len(scouterNameList) < 6:
        scouterNameList.append('')
    if selectMatch:
        match = matches[selectMatch - 1]
        ref = db.collection("matches").document("8020").collection("2025_San_Diego")
        status = {} # {'0000:true,9999:false},...
        for team in match['alliances']['blue']['team_keys']:
            teamNumber = team.replace('frc','')
            #check Qualifications_{match_number}_{teamNumber} exists
            status[team] = ref.document(f"Qualifications_{selectMatch}_{teamNumber}").get().exists
        for team in match['alliances']['red']['team_keys']:
            teamNumber = team.replace('frc','')
            #check Qualifications_{match_number}_{teamNumber} exists
            status[team] = ref.document(f"Qualifications_{selectMatch}_{teamNumber}").get().exists
        time = datetime.datetime.fromtimestamp(match['time'])
        st.markdown(f"### Match {match['match_number']} at {time}")
        st.markdown(f"""
                    | Blue 1 | Blue 2 | Blue 3 || Red 1 | Red 2 | Red 3 |
                    | --- | --- | --- | --- | --- | --- | --- |
                    | {match['alliances']['blue']['team_keys'][0].replace('frc','')} | {match['alliances']['blue']['team_keys'][1].replace('frc','')} | {match['alliances']['blue']['team_keys'][2].replace('frc','')} | | {match['alliances']['red']['team_keys'][0].replace('frc','')} | {match['alliances']['red']['team_keys'][1].replace('frc','')} | {match['alliances']['red']['team_keys'][2].replace('frc','')} |
                    | {'✅' if status[match['alliances']['blue']['team_keys'][0]] else '❌'}|{'✅' if status[match['alliances']['blue']['team_keys'][1]] else '❌'}|{'✅' if status[match['alliances']['blue']['team_keys'][2]] else '❌'}| |{'✅' if status[match['alliances']['red']['team_keys'][0]] else '❌'}|{'✅' if status[match['alliances']['red']['team_keys'][1]] else '❌'}|{'✅' if status[match['alliances']['red']['team_keys'][2]] else '❌'}|
                    | {scouterNameList[3]}|{scouterNameList[4]}|{scouterNameList[5]}||{scouterNameList[0]}|{scouterNameList[1]}|{scouterNameList[2]}|
                    """)
else:
    st.warning("Invalid User Name or Serial Code")
    st.stop()