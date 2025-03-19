import streamlit as st
import pandas as pd
import pdfplumber
import fitz  # PyMuPDF
import pdf2txt
from bs4 import BeautifulSoup
import re
import os

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

def extract_text_pdfplumber(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            if text.strip():
                return text
    except Exception as e:
        st.warning(f"⚠️ pdfplumber failed: {e}")
    return None

def extract_text_pymupdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()
        if text.strip():
            return text
    except Exception as e:
        st.warning(f"⚠️ PyMuPDF failed: {e}")
    return None

def extract_text_html(pdf_path):
    try:
        html_path = "output.html"
        pdf2txt.main(["-o", html_path, pdf_path])
        with open(html_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
            text = soup.get_text()
        os.remove(html_path)
        return text
    except Exception as e:
        st.warning(f"⚠️ HTML extraction failed: {e}")
        return None

# Submit button
if st.button("Submit") and im_pdf:
    club_players = set()
    if club_csvs:
        for club_csv in club_csvs:
            club_df = pd.read_csv(club_csv, skiprows=3)
            club_df = club_df[club_df['Status'].str.strip().str.upper() == 'OK']
            club_df['Full Name'] = club_df['Person'].apply(lambda x: ' '.join(x.strip().lower().split(', ')[::-1]))
            club_players.update(club_df['Full Name'])

    # Extract text from PDF
    text = extract_text_pdfplumber(im_pdf)
    if text is None:
        st.write("🔄 pdfplumber failed, trying PyMuPDF...")
        text = extract_text_pymupdf(im_pdf)
    if text is None:
        st.write("🔄 PyMuPDF failed, trying HTML extraction...")
        text = extract_text_html(im_pdf)
    
    teams = {}
    elite_players = set()
    elite_teams = {}
    
    if text:
        lines = text.split("\n")
        current_team = None
        recording_players = False
        current_level = "Regular"
    
        for line in lines:
            if "Oregon State University" in line or "imleagues.com" in line or re.match(r'\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} [APap][Mm]', line):
                continue
            if "->" in line:
                current_level = "Elite" if "Elite" in line else "Regular"
                continue
            match = re.match(r"(.+?)Rosters", line)
            if match:
                current_team = match.group(1).strip()
                teams[current_team] = []
                if current_level == "Elite":
                    elite_teams[current_team] = "Elite"
                recording_players = False
                continue
            if "Name Gender Status" in line:
                recording_players = True
                continue
            if recording_players and line.strip():
                player_name = line.split(" Male ")[0].split(" Female ")[0].strip()
                player_name = re.sub(r"^C-", "", player_name, flags=re.IGNORECASE)
                player_name = re.sub(r"\(Nomad\)$", "", player_name, flags=re.IGNORECASE)
                player_name = player_name.lower()
                if current_team in elite_teams:
                    elite_players.add(player_name)
                if current_team:
                    teams[current_team].append(player_name)
    
        club_players.update(elite_players)
        violations = {}
        team_club_members = {}
    
        for team, roster in teams.items():
            if team in elite_teams:
                continue  
            club_on_team = [player.title() for player in roster if player in club_players]
            team_club_members[team] = club_on_team
            if len(club_on_team) > max_club_players:
                violations[team] = len(club_on_team)
    
        # Output violations
        if violations:
            st.header(f"🚫 Teams Violating Club Player Limit (> {max_club_players} per team):")
            for team, count in violations.items():
                st.write(f"- **{team}** has **{count}** club players.")
        else:
            st.success(f"✅ No teams violating the {max_club_players} club player limit!")
    
        # Summary of all teams with club players
        st.header("Summary of Club Players on Rosters:")
        for team, members in team_club_members.items():
            if members:
                if team in violations:
                    st.markdown(
                        f"**<span style='color:red;'>{team}</span>:** {', '.join(members)}",
                        unsafe_allow_html=True
                    )
                else:
                    st.write(f"**{team}:** {', '.join(members)}")
    else:
        st.error("❌ Text extraction failed for all methods.")
