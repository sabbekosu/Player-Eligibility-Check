import streamlit as st
import pandas as pd
import pdfplumber
import re

# Streamlit Title
st.title("IM Team Club Player Checker")

# Selector for max club players allowed
st.header("Sport Rules Configuration")
player_limit = st.selectbox(
    "How many players are in the game at one time?",
    ["5 or fewer players (max 1 club player)", "6 or more players (max 2 club players)"]
)

# Set violation threshold based on selection
max_club_players = 1 if "5 or fewer" in player_limit else 2

# Upload multiple CSVs for club rosters (optional)
club_csvs = st.file_uploader("Upload Club Roster CSV(s) (Optional)", type="csv", accept_multiple_files=True)

# Upload PDF for IM Team Rosters
im_pdf = st.file_uploader("Upload IM Team Rosters PDF", type="pdf")

# Submit button
if st.button("Submit") and im_pdf:
    # Combine all club players from multiple CSV files (if any exist)
    club_players = set()

    if club_csvs:  # Only process CSVs if provided
        for club_csv in club_csvs:
            club_df = pd.read_csv(club_csv, skiprows=3)
            club_df = club_df[club_df['Status'].str.strip().str.upper() == 'OK']
            club_df['Full Name'] = club_df['Person'].apply(lambda x: ' '.join(x.strip().lower().split(', ')[::-1]))
            club_players.update(club_df['Full Name'])  # Add names to the combined set

    # Dictionary to store teams and their rosters
    teams = {}
    elite_players = set()  # Set to store all elite team players
    elite_teams = {}  # Dictionary to track elite teams {team_name: "Elite"}

    # Parse PDF using pdfplumber
    with pdfplumber.open(im_pdf) as pdf:
        current_team = None
        recording_players = False  # Flag to track when we're inside a roster
        current_level = "Regular"  # Default team level is Regular

        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")

            for i, line in enumerate(lines):
                # Ignore unnecessary headers like "Oregon State University"
                if "Oregon State University" in line:
                    continue

                # Detect team level using "->" for flexibility
                if "->" in line:
                    current_level = "Elite" if "Elite" in line else "Regular"
                    continue  # Move to the next line, which should contain the team name

                # Detect team name from "XYZRosters"
                match = re.match(r"(.+?)Rosters", line)
                if match:
                    current_team = match.group(1).strip()  # Extract just the team name
                    teams[current_team] = []
                    
                    if current_level == "Elite":
                        elite_teams[current_team] = "Elite"  # Mark this as an elite team
                    
                    recording_players = False  # Stop recording until we hit "Name Gender Status..."
                    continue

                # Detect start of player list
                if "Name Gender Status" in line:
                    recording_players = True
                    continue

                # If we're recording players, extract names
                if recording_players and line.strip():
                    # Only take the first part (player name) and ignore everything else
                    player_name = line.split(" Male ")[0].split(" Female ")[0].strip()

                    # Remove "C-" at the start and "(Nomad)" at the end
                    player_name = re.sub(r"^C-", "", player_name, flags=re.IGNORECASE)  # Remove "C-" from the start
                    player_name = re.sub(r"\(Nomad\)$", "", player_name, flags=re.IGNORECASE)  # Remove "(Nomad)" from the end
                    player_name = player_name.lower()  # Convert to lowercase for consistency

                    # If the team is elite, add players to the elite player set
                    if current_team in elite_teams:
                        elite_players.add(player_name)

                    # Add cleaned name to the team's roster
                    if current_team:
                        teams[current_team].append(player_name)

    # Update club players list to include elite players
    club_players.update(elite_players)

    # Matching club players and rule violations
    violations = {}
    team_club_members = {}

    for team, roster in teams.items():
        # Skip elite teams when checking violations
        if team in elite_teams:
            continue  

        # Check for club players (including elite players)
        club_on_team = [player.title() for player in roster if player in club_players]
        team_club_members[team] = club_on_team

        if len(club_on_team) > max_club_players:
            violations[team] = len(club_on_team)

    # Output violations
    if violations:
        st.header(f"🚫 Teams Violating Club Player Limit (>{max_club_players} per team):")
        for team, count in violations.items():
            st.write(f"- **{team}** has **{count}** club players.")
    else:
        st.success(f"✅ No teams violating the {max_club_players} club player limit!")

    # Summary of all teams with club players
    st.header("Summary of Club Players on Rosters:")
    for team, members in team_club_members.items():
        if members:
            # Highlight teams in red only if they violate the club player limit
            if team in violations:
                st.markdown(
                    f"**<span style='color:red;'>{team}</span>:** {', '.join(members)}",
                    unsafe_allow_html=True
                )
            else:
                st.write(f"**{team}:** {', '.join(members)}")