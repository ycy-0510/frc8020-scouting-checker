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


def check_valid_score(doc):
    if not doc.exists:
        return False
    data = doc.to_dict() or {}
    try:
        auto = data.get("auto", {})
        if bool(auto.get("score")) != (auto.get("fuels", 0) >= 5): return False
        
        teleop = data.get("teleop", {})
        if bool(teleop.get("scoreT")) != (teleop.get("transitionfuels", 0) >= 5): return False
        
        for f, s in zip(teleop.get("shiftsfuels", []), teleop.get("score", [])):
            if bool(s) != (f >= 5): return False
            
        endgame = data.get("endgame", {})
        if bool(endgame.get("score")) != (endgame.get("endfuels", 0) >= 5): return False
        
        return True
    except Exception:
        return False


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
serialCode = st.text_input("Enter Serial Code: ", type="password")
if user in st.secrets["serial"] and serialCode == st.secrets["serial"][user]:
    tba_api_key = st.secrets["tba"]["API"]

    # Construct the API URL
    api_url = f"https://www.thebluealliance.com/api/v3/event/2026ilch/matches"
    headers = {"X-TBA-Auth-Key": tba_api_key}

    # get match results from TBA
    matchResultRes = requests.get(api_url, headers=headers)
    matchResultRes.raise_for_status()  # Raise an exception for bad status codes
    matchResults = matchResultRes.json()
    # sort match by mac number
    matchResults.sort(key=lambda x: x["match_number"])
    ##show win/loss and score
    st.sidebar.markdown("### Match Results")
    for matchResult in matchResults:
        st.sidebar.markdown(f"### Match {matchResult['match_number']}")
        st.sidebar.markdown(
            f"""
                    ||1|2|3|Score|
                    |---|---|---|---|---|
                    |Blue|{matchResult['alliances']['blue']['team_keys'][0].replace('frc','')}|{matchResult['alliances']['blue']['team_keys'][1].replace('frc','')}|{matchResult['alliances']['blue']['team_keys'][2].replace('frc','')}|{matchResult['alliances']['blue']['score']}|
                    |Red|{matchResult['alliances']['red']['team_keys'][0].replace('frc','')}|{matchResult['alliances']['red']['team_keys'][1].replace('frc','')}|{matchResult['alliances']['red']['team_keys'][2].replace('frc','')}|{matchResult['alliances']['red']['score']}|"""
        )
        st.sidebar.markdown(f"{matchResult['winning_alliance']} Alliance Wins")
        if matchResult["actual_time"] != None:
            st.sidebar.markdown(
                f"Time: {datetime.datetime.fromtimestamp(matchResult['actual_time'])}"
            )
            if matchResult["score_breakdown"] != None:
                st.sidebar.markdown(f"### Score Breakdown")
                st.sidebar.markdown(f"Blue Alliance:")
                st.sidebar.markdown(
                    f"Total Points: {matchResult['score_breakdown']['blue']['totalPoints']}"
                )
                st.sidebar.markdown(
                    f"RP: {matchResult['score_breakdown']['blue']['rp']}(+{1 if matchResult['score_breakdown']['blue']['energizedAchieved'] else 0}+{1 if matchResult['score_breakdown']['blue']['superchargedAchieved'] else 0}+{1 if matchResult['score_breakdown']['blue']['traversalAchieved'] else 0})"
                )
                st.sidebar.markdown(
                    f"Panalty: {matchResult['score_breakdown']['blue']['majorFoulCount']}/{matchResult['score_breakdown']['blue']['minorFoulCount']}"
                )
                st.sidebar.markdown(f"Red Alliance:")
                st.sidebar.markdown(
                    f"Total Points: {matchResult['score_breakdown']['red']['totalPoints']}"
                )
                st.sidebar.markdown(
                    f"RP: {matchResult['score_breakdown']['red']['rp']}(+{1 if matchResult['score_breakdown']['red']['energizedAchieved'] else 0}+{1 if matchResult['score_breakdown']['red']['superchargedAchieved'] else 0}+{1 if matchResult['score_breakdown']['red']['traversalAchieved'] else 0})"
                )
                st.sidebar.markdown(
                    f"Penalty: {matchResult['score_breakdown']['red']['majorFoulCount']}/{matchResult['score_breakdown']['red']['minorFoulCount']}"
                )
                # score_breakdown/videos
            if len(matchResult["videos"]) > 0:
                st.sidebar.link_button(
                    "Watch Video",
                    f"https://www.youtube.com/watch?v={matchResult['videos'][0]['key']}",
                )
        else:
            st.sidebar.markdown(
                f"Time*: {datetime.datetime.fromtimestamp(matchResult['time'])}"
            )
        # st.sidebar.markdown(matchResult)

    ##==================Scouting Checker==================
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes

    matches = response.json()
    # sort match by mac number
    matches.sort(key=lambda x: x["match_number"])
    # Parse the response and extract the relevant information
    matchNumbers = [match["match_number"] for match in matches]
    selectMatch = st.selectbox("Select Match Number: ", matchNumbers)
    if selectMatch:
        match = matches[selectMatch - 1]
        ref = db.collection("matches").document("8020").collection("2026_Midwest")
        submit = {}
        status = {}  # {'0000:true,9999:false},...
        shift = {}
        rp_match = {}
        score_match = {}
        blue_teams = match["alliances"]["blue"]["team_keys"]
        red_teams = match["alliances"]["red"]["team_keys"]

        # get official RP & Score from TBA
        tba_blue_rp = match.get("score_breakdown", {}).get("blue", {}).get("rp") if match.get("score_breakdown") else None
        tba_red_rp = match.get("score_breakdown", {}).get("red", {}).get("rp") if match.get("score_breakdown") else None

        tba_blue_score = match.get("score_breakdown", {}).get("blue", {}).get("totalPoints") if match.get("score_breakdown") else None
        tba_red_score = match.get("score_breakdown", {}).get("red", {}).get("totalPoints") if match.get("score_breakdown") else None

        for team in blue_teams:
            teamNumber = team.replace("frc", "")
            # check if score bool matches fuels >= 5
            doc = ref.document(f"Qualifications_{selectMatch}_{teamNumber}").get()
            submit[team] = doc.exists
            status[team] = check_valid_score(doc)
            data = doc.to_dict() if doc.exists else None
            res_data = data.get("result", {}) if data else {}
            shift[team] = res_data.get("shift1Active")
            
            # Check RP
            scouted_rp = res_data.get("rankingPoints")
            rp_match[team] = (scouted_rp == tba_blue_rp) if tba_blue_rp is not None and scouted_rp is not None else None
            
            # Check Score
            scouted_score = res_data.get("totalScore")
            score_match[team] = (scouted_score == tba_blue_score) if tba_blue_score is not None and scouted_score is not None else None

        for team in red_teams:
            teamNumber = team.replace("frc", "")
            # check if score bool matches fuels >= 5
            doc = ref.document(f"Qualifications_{selectMatch}_{teamNumber}").get()
            submit[team] = doc.exists
            status[team] = check_valid_score(doc)
            data = doc.to_dict() if doc.exists else None
            res_data = data.get("result", {}) if data else {}
            shift[team] = res_data.get("shift1Active")

            # Check RP
            scouted_rp = res_data.get("rankingPoints")
            rp_match[team] = (scouted_rp == tba_red_rp) if tba_red_rp is not None and scouted_rp is not None else None

            # Check Score
            scouted_score = res_data.get("totalScore")
            score_match[team] = (scouted_score == tba_red_score) if tba_red_score is not None and scouted_score is not None else None
            
        
        
        blue_shifts = [shift[t] for t in blue_teams if shift[t] is not None]
        red_shifts = [shift[t] for t in red_teams if shift[t] is not None]
        
        blue_same = (len(set(blue_shifts)) == 1 and len(blue_shifts) == 3)
        blue_val = blue_shifts[0] if blue_same else None
        
        red_same = (len(set(red_shifts)) == 1 and len(red_shifts) == 3)
        red_val = red_shifts[0] if red_same else None
        
        diff_check = (blue_same and red_same and blue_val != red_val)
        
        time = datetime.datetime.fromtimestamp(match["time"])
        st.markdown(f"### Match {match['match_number']} at {time}")
        st.markdown(
            f"""
                    | | Blue 1 | Blue 2 | Blue 3 || Red 1 | Red 2 | Red 3 |
                    | --- | --- | --- | --- | --- | --- | --- | --- |
                    | Team| {blue_teams[0].replace('frc','')} | {blue_teams[1].replace('frc','')} | {blue_teams[2].replace('frc','')} | | {red_teams[0].replace('frc','')} | {red_teams[1].replace('frc','')} | {red_teams[2].replace('frc','')} |
                    | Submit| {'✅' if submit[blue_teams[0]] else '❌'}|{'✅' if submit[blue_teams[1]] else '❌'}|{'✅' if submit[blue_teams[2]] else '❌'}| |{'✅' if submit[red_teams[0]] else '❌'}|{'✅' if submit[red_teams[1]] else '❌'}|{'✅' if submit[red_teams[2]] else '❌'}|
                    | Valid | {'✅' if status[blue_teams[0]] else '❌'}|{'✅' if status[blue_teams[1]] else '❌'}|{'✅' if status[blue_teams[2]] else '❌'}| |{'✅' if status[red_teams[0]] else '❌'}|{'✅' if status[red_teams[1]] else '❌'}|{'✅' if status[red_teams[2]] else '❌'}|
                    | RP    | {'✅' if rp_match[blue_teams[0]] else '❌'}|{'✅' if rp_match[blue_teams[1]] else '❌'}|{'✅' if rp_match[blue_teams[2]] else '❌'}| |{'✅' if rp_match[red_teams[0]] else '❌'}|{'✅' if rp_match[red_teams[1]] else '❌'}|{'✅' if rp_match[red_teams[2]] else '❌'}|
                    | Score | {'✅' if score_match[blue_teams[0]] else '❌'}|{'✅' if score_match[blue_teams[1]] else '❌'}|{'✅' if score_match[blue_teams[2]] else '❌'}| |{'✅' if score_match[red_teams[0]] else '❌'}|{'✅' if score_match[red_teams[1]] else '❌'}|{'✅' if score_match[red_teams[2]] else '❌'}|
                    """
        )
        st.markdown(f"**Blue Match:** {'✅' if blue_same else '❌'} | **Red Match:** {'✅' if red_same else '❌'} | **Blue & Red Different:** {'✅' if diff_check else '❌'}")

else:
    st.warning("Invalid User Name or Serial Code")
    st.stop()
