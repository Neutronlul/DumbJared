import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os
from dotenv import load_dotenv
import gspread
import re
from datetime import datetime


ua = UserAgent()

load_dotenv()

url = os.getenv("TARGET_URL")
key = os.getenv("SHEET_KEY")
subSheet = os.getenv("SUBSHEET")
credentialsFile = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

gc = gspread.service_account(filename=credentialsFile)


def fetchPage():
    r = requests.get(url, headers={"User-Agent": ua.random})
    if r.ok:
        return BeautifulSoup(r.content, "html.parser")
    else:
        raise Exception(f"Failed to retrieve: {r.status_code}")


def buildRows(soup):
    rows = []

    for instance in soup.find_all("div", class_="venue_recap"):
        # get quizmaster
        qm = (
            instance.find("div", class_="recap_meta")
            .find(string=re.compile(r"by Quizmaster"))
            .replace("by Quizmaster", "")
            .strip()
        )

        # get date
        rawDate = (
            instance.find("div", class_="recap_meta")
            .find(string=re.compile(r"(?:[A-Z][a-z]{2} ){2}\d{1,2} \d{4}"))
            .strip()
        )

        # format date
        dtDate = datetime.strptime(rawDate, "%a %b %d %Y")
        ISODate = dtDate.strftime("%Y-%m-%d")

        # create rows from table
        for team in (
            instance.find("table", class_="recap_table").find("tbody").find_all("tr")
        ):
            # get team name
            teamName = team.find_all("td")[2].text.strip()

            # get team id; sometimes absent
            try:
                teamID = int(team.find_all("td")[1].text.strip())
            except:
                teamID = None

            # get team score
            teamScore = int(team.find_all("td")[3].text.strip())

            # construct row
            row = [ISODate, teamScore, qm, teamName, teamID]
            rows.append(row)

    # sort by date ascending, then score descending
    return sorted(rows, key=lambda x: (x[0], -x[1]))


def appendToSheet(data):
    sh = gc.open_by_key(key).worksheet(subSheet)
    sh.append_rows(data, value_input_option="USER_ENTERED")


def main():
    # scrape the page
    soup = fetchPage()

    # construct rows from the page
    data = buildRows(soup)

    # apppend the rows to the sheet
    appendToSheet(data)


if __name__ == "__main__":
    main()
