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

# add check total
def check_team_score(doc):
    if not doc.exists:
        return 0
    data = doc.to_dict() or {}
    ret = 0
    try:
        auto = data.get("auto", {})
        ret += auto.get("fuels", 0)
        
        teleop = data.get("teleop", {})
        ret += teleop.get("transitionfuels", 0)
        
        for f in teleop.get("shiftsfuels", []):
            ret += f
            
        endgame = data.get("endgame", {})
        ret += endgame.get("endfuels", 0)
        
        return ret
    except Exception:
        return 0


def get_team_shift_fuels(doc):
    """Returns a list of per-shift fuel counts [shift1, shift2, shift3, shift4]."""
    if not doc.exists:
        return [0, 0, 0, 0]
    data = doc.to_dict() or {}
    try:
        teleop = data.get("teleop", {})
        fuels = teleop.get("shiftsfuels", [])
        result = [fuels[i] if i < len(fuels) else 0 for i in range(4)]
        return result
    except Exception:
        return [0, 0, 0, 0]


def get_team_breakdown(doc):
    """Returns (auto, transition, shifts[4], endgame) fuel counts."""
    if not doc.exists:
        return 0, 0, [0, 0, 0, 0], 0
    data = doc.to_dict() or {}
    try:
        auto_f = data.get("auto", {}).get("fuels", 0)
        teleop = data.get("teleop", {})
        trans_f = teleop.get("transitionfuels", 0)
        raw = teleop.get("shiftsfuels", [])
        shifts_f = [raw[i] if i < len(raw) else 0 for i in range(4)]
        end_f = data.get("endgame", {}).get("endfuels", 0)
        return auto_f, trans_f, shifts_f, end_f
    except Exception:
        return 0, 0, [0, 0, 0, 0], 0

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
    tab1, tab2 = st.tabs(["Qualification", "Practice"])

    with tab1:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Filter for qualification matches only
        matches = [m for m in response.json() if m["comp_level"] == "qm"]
        # Sort matches by match number
        matches.sort(key=lambda x: x["match_number"])
        
        # Create a mapping from match number to match object for robust selection
        match_map = {m["match_number"]: m for m in matches}
        match_numbers = sorted(match_map.keys())
        
        selectMatch = st.selectbox("Select Match Number: ", match_numbers)
        
        if selectMatch:
            match = match_map[selectMatch]
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

            # total score and detailed scouted counts
            blue_total = 0
            red_total = 0
            blue_auto_total = 0
            red_auto_total = 0
            blue_trans_total = 0
            red_trans_total = 0
            blue_shift_totals = [0, 0, 0, 0]
            red_shift_totals = [0, 0, 0, 0]
            blue_end_total = 0
            red_end_total = 0

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

                # Total Score & detailed breakdown
                auto_f, trans_f, shifts_f, end_f = get_team_breakdown(doc)
                blue_auto_total += auto_f
                blue_trans_total += trans_f
                for i, v in enumerate(shifts_f):
                    blue_shift_totals[i] += v
                blue_end_total += end_f
                blue_total += auto_f + trans_f + sum(shifts_f) + end_f

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

                # Total Score & detailed breakdown
                auto_f, trans_f, shifts_f, end_f = get_team_breakdown(doc)
                red_auto_total += auto_f
                red_trans_total += trans_f
                for i, v in enumerate(shifts_f):
                    red_shift_totals[i] += v
                red_end_total += end_f
                red_total += auto_f + trans_f + sum(shifts_f) + end_f

            # TBA detailed counts from hubScore
            hub_blue = match.get("score_breakdown", {}).get("blue", {}).get("hubScore", {}) if match.get("score_breakdown") else {}
            hub_red  = match.get("score_breakdown", {}).get("red",  {}).get("hubScore", {}) if match.get("score_breakdown") else {}
            tba_blue_auto  = hub_blue.get("autoCount", 0)
            tba_red_auto   = hub_red.get("autoCount", 0)
            tba_blue_trans = hub_blue.get("transitionCount", 0)
            tba_red_trans  = hub_red.get("transitionCount", 0)
            tba_blue_shifts = [hub_blue.get(f"shift{i+1}Count", 0) for i in range(4)]
            tba_red_shifts  = [hub_red.get(f"shift{i+1}Count",  0) for i in range(4)]
            tba_blue_end   = hub_blue.get("endgameCount", 0)
            tba_red_end    = hub_red.get("endgameCount", 0)
            tba_blue_total_count = hub_blue.get("totalCount", 0)
            tba_red_total_count  = hub_red.get("totalCount", 0)
            
            blue_error = blue_total - tba_blue_total_count
            red_error  = red_total  - tba_red_total_count
            
            blue_shift_errors = [blue_shift_totals[i] - tba_blue_shifts[i] for i in range(4)]
            red_shift_errors  = [red_shift_totals[i]  - tba_red_shifts[i]  for i in range(4)]
                
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

            # Detailed score error breakdown table
            st.markdown("#### Score Error Breakdown")
            def err_str(e):
                return f"+{e}" if e > 0 else str(e)
            st.markdown(
                f"""
| | Blue Scouted | Blue TBA | Blue Error | | Red Scouted | Red TBA | Red Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Auto | {blue_auto_total} | {tba_blue_auto} | {err_str(blue_auto_total - tba_blue_auto)} | | {red_auto_total} | {tba_red_auto} | {err_str(red_auto_total - tba_red_auto)} |
| Transition | {blue_trans_total} | {tba_blue_trans} | {err_str(blue_trans_total - tba_blue_trans)} | | {red_trans_total} | {tba_red_trans} | {err_str(red_trans_total - tba_red_trans)} |
| Shift 1 | {blue_shift_totals[0]} | {tba_blue_shifts[0]} | {err_str(blue_shift_errors[0])} | | {red_shift_totals[0]} | {tba_red_shifts[0]} | {err_str(red_shift_errors[0])} |
| Shift 2 | {blue_shift_totals[1]} | {tba_blue_shifts[1]} | {err_str(blue_shift_errors[1])} | | {red_shift_totals[1]} | {tba_red_shifts[1]} | {err_str(red_shift_errors[1])} |
| Shift 3 | {blue_shift_totals[2]} | {tba_blue_shifts[2]} | {err_str(blue_shift_errors[2])} | | {red_shift_totals[2]} | {tba_red_shifts[2]} | {err_str(red_shift_errors[2])} |
| Shift 4 | {blue_shift_totals[3]} | {tba_blue_shifts[3]} | {err_str(blue_shift_errors[3])} | | {red_shift_totals[3]} | {tba_red_shifts[3]} | {err_str(red_shift_errors[3])} |
| Endgame | {blue_end_total} | {tba_blue_end} | {err_str(blue_end_total - tba_blue_end)} | | {red_end_total} | {tba_red_end} | {err_str(red_end_total - tba_red_end)} |
| **Total** | **{blue_total}** | **{tba_blue_total_count}** | **{err_str(blue_error)}** | | **{red_total}** | **{tba_red_total_count}** | **{err_str(red_error)}** |
"""
            )

    with tab2:
        practiceMatch = st.number_input("Practice Match Number: ", min_value=1, step=1)
        col1, col2 = st.columns(2)
        blue_practice_teams = []
        red_practice_teams = []
        with col1:
            st.markdown("### Blue Alliance")
            for i in range(3):
                team = st.text_input(f"Blue {i+1} Team Number: ", key=f"blue_practice_{i}")
                if team: blue_practice_teams.append(team)
        with col2:
            st.markdown("### Red Alliance")
            for i in range(3):
                team = st.text_input(f"Red {i+1} Team Number: ", key=f"red_practice_{i}")
                if team: red_practice_teams.append(team)
        
        if practiceMatch and len(blue_practice_teams) == 3 and len(red_practice_teams) == 3:
            ref = db.collection("matches").document("8020").collection("2026_Midwest")
            submit_p = {}
            status_p = {}
            shift_p = {}
            
            blue_total = 0
            red_total = 0

            for teamNumber in blue_practice_teams:
                # Assuming practice matches are stored with 'Practice_' prefix
                doc = ref.document(f"Practice_{practiceMatch}_{teamNumber}").get()
                submit_p[teamNumber] = doc.exists
                status_p[teamNumber] = check_valid_score(doc)
                data = doc.to_dict() if doc.exists else None
                res_data = data.get("result", {}) if data else {}
                shift_p[teamNumber] = res_data.get("shift1Active")
                # Total Score
                blue_total += check_team_score(doc)              
                blue_scouted_score = res_data.get("totalScore")  
                
            for teamNumber in red_practice_teams:
                doc = ref.document(f"Practice_{practiceMatch}_{teamNumber}").get()
                submit_p[teamNumber] = doc.exists
                status_p[teamNumber] = check_valid_score(doc)
                data = doc.to_dict() if doc.exists else None
                res_data = data.get("result", {}) if data else {}
                shift_p[teamNumber] = res_data.get("shift1Active")
                # Total Score
                red_total += check_team_score(doc)            
                red_scouted_score = res_data.get("totalScore")    
                
            blue_error, red_error = blue_total - blue_scouted_score, red_total - red_scouted_score
                
            blue_shifts_p = [shift_p[t] for t in blue_practice_teams if shift_p[t] is not None]
            red_shifts_p = [shift_p[t] for t in red_practice_teams if shift_p[t] is not None]
            
            blue_same_p = (len(set(blue_shifts_p)) == 1 and len(blue_shifts_p) == 3)
            blue_val_p = blue_shifts_p[0] if blue_same_p else None
            
            red_same_p = (len(set(red_shifts_p)) == 1 and len(red_shifts_p) == 3)
            red_val_p = red_shifts_p[0] if red_same_p else None
            
            diff_check_p = (blue_same_p and red_same_p and blue_val_p != red_val_p)
            
            st.markdown(f"### Practice Match {practiceMatch}")
            st.markdown(
                f"""
                        | | Blue 1 | Blue 2 | Blue 3 || Red 1 | Red 2 | Red 3 |
                        | --- | --- | --- | --- | --- | --- | --- | --- |
                        | Team| {blue_practice_teams[0]} | {blue_practice_teams[1]} | {blue_practice_teams[2]} | | {red_practice_teams[0]} | {red_practice_teams[1]} | {red_practice_teams[2]} |
                        | Submit| {'✅' if submit_p[blue_practice_teams[0]] else '❌'}|{'✅' if submit_p[blue_practice_teams[1]] else '❌'}|{'✅' if submit_p[blue_practice_teams[2]] else '❌'}| |{'✅' if submit_p[red_practice_teams[0]] else '❌'}|{'✅' if submit_p[red_practice_teams[1]] else '❌'}|{'✅' if submit_p[red_practice_teams[2]] else '❌'}|
                        | Valid | {'✅' if status_p[blue_practice_teams[0]] else '❌'}|{'✅' if status_p[blue_practice_teams[1]] else '❌'}|{'✅' if status_p[blue_practice_teams[2]] else '❌'}| |{'✅' if status_p[red_practice_teams[0]] else '❌'}|{'✅' if status_p[red_practice_teams[1]] else '❌'}|{'✅' if status_p[red_practice_teams[2]] else '❌'}|
                        """
            )
            st.markdown(f"**Blue Match:** {'✅' if blue_same_p else '❌'} | **Red Match:** {'✅' if red_same_p else '❌'} | **Blue & Red Different:** {'✅' if diff_check_p else '❌'} | **Blue Error:** {blue_error} | **Red Error:** {red_error}")

else:
    st.warning("Invalid User Name or Serial Code")
    st.stop()
