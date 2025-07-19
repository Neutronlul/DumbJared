import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from dotenv import load_dotenv
import gspread


load_dotenv()

baseURL = os.getenv("TARGET_URL")
key = os.getenv("SHEET_KEY")
subSheet = os.getenv("SUBSHEET")
credentialsFile = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

ua = UserAgent()

gc = gspread.service_account(filename=credentialsFile)


def get_datetime_input(prompt="Enter date: ", fmt="%Y-%m-%d"):
    """
    Get user input for a date object with default value of 2024-08-08.

    Args:
        prompt (str): The prompt message to display to the user
        fmt (str): Expected date format string

    Returns:
        datetime: The parsed date object or default value
    """
    default = datetime(2024, 8, 8)

    while True:
        try:
            user_input = input(
                f"{prompt}(default: {default.strftime('%Y-%m-%d')}, format: {fmt}): "
            ).strip()

            # If user just presses enter, return the default
            if not user_input:
                return default

            # Try to parse the input
            return datetime.strptime(user_input, fmt)

        except ValueError as e:
            print(f"Invalid date format. Please use {fmt} format.")
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None


def fetchPage(url):
    r = requests.get(url, headers={"User-Agent": ua.random})
    if r.ok:
        return BeautifulSoup(r.content, "html.parser")
    else:
        raise Exception(f"Failed to retrieve: {r.status_code}")


def buildRows(soup, rows=[]):
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
    # # scrape the page
    # soup = fetchPage(baseURL + "1")

    # # construct rows from the page
    # data = buildRows(soup)

    # # apppend the rows to the sheet
    # appendToSheet(data)

    endDate = get_datetime_input()
    pageCounter = 1
    rows = []
    while True:
        rows = buildRows(fetchPage(baseURL + str(pageCounter)), rows)
        pageCounter += 1
        print(f"Scraped page {pageCounter - 1} with {len(rows)} total rows")

        if rows and datetime.strptime(rows[0][0], "%Y-%m-%d") <= endDate:
            break

    appendToSheet(rows)


if __name__ == "__main__":
    main()
