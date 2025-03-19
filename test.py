import pdfplumber
import fitz  # PyMuPDF
import pdf2txt
from bs4 import BeautifulSoup
import re
import os
import pandas as pd

# File paths
club_csvs = []  # Empty list, allowing no CSVs to be uploaded
im_pdf = "imbasketball.pdf"

# Combine all club players from multiple CSV files (if any exist)
club_players = set()

if club_csvs:
    for club_csv in club_csvs:
        club_df = pd.read_csv(club_csv, skiprows=3)
        club_df = club_df[club_df['Status'].str.strip().str.upper() == 'OK']
        club_df['Full Name'] = club_df['Person'].apply(lambda x: ' '.join(x.strip().lower().split(', ')[::-1]))
        club_players.update(club_df['Full Name'])

def extract_text_pdfplumber(pdf_path):
    """Attempts to extract text using pdfplumber."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            if text.strip():
                return text
    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")
    return None

def extract_text_pymupdf(pdf_path):
    """Attempts to extract text using PyMuPDF (fitz)."""
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()
        if text.strip():
            return text
    except Exception as e:
        print(f"⚠️ PyMuPDF failed: {e}")
    return None

def extract_text_html(pdf_path):
    """Extracts text by converting the PDF to HTML first."""
    try:
        html_path = "output.html"
        pdf2txt.main(["-o", html_path, pdf_path])

        with open(html_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
            text = soup.get_text()

        os.remove(html_path)
        return text
    except Exception as e:
        print(f"⚠️ HTML extraction failed: {e}")
        return None

# Attempt text extraction
text = extract_text_pdfplumber(im_pdf)
if text is None:
    print("🔄 pdfplumber failed, trying PyMuPDF...")
    text = extract_text_pymupdf(im_pdf)

if text is None:
    print("🔄 PyMuPDF failed, trying HTML extraction...")
    text = extract_text_html(im_pdf)

# Dictionary to store teams and their rosters
teams = {}
elite_players = set()
elite_teams = {}

if text:
    lines = text.split("\n")
    current_team = None
    recording_players = False
    current_level = "Regular"

    for line in lines:
        if "Oregon State University" in line:
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

    # Matching club players and rule violations
    violations = {}
    team_club_members = {}

    for team, roster in teams.items():
        if team in elite_teams:
            continue  

        club_on_team = [player.title() for player in roster if player in club_players]
        team_club_members[team] = club_on_team

        if len(club_on_team) > 2:
            violations[team] = len(club_on_team)

    # Output violations
    print("\n🚫 Teams Violating Club Player Limit (>2 per team):")
    if violations:
        for team, count in violations.items():
            print(f"- {team} has {count} club players")
    else:
        print("✅ No teams violating the rule.")

    # Summary of all teams with club players (excluding elite teams)
    print("\n📋 Summary of Club Players on Rosters:")
    for team, members in team_club_members.items():
        if members:
            if team in violations:
                print(f"🔴 {team}: {', '.join(members)}")
            else:
                print(f"{team}: {', '.join(members)}")
else:
    print("❌ Text extraction failed for all methods.")