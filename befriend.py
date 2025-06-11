import sys
import json
import getopt
from getpass import getpass
from datetime import datetime
from time import sleep
from random import randint
from random import uniform as rand
from playwright.sync_api import sync_playwright

USERNAME = "sap.love__"
PASSWORD = ""
SESS_FILE = ".befriend.sess"

MAX_LIKES = randint(70,80)
MAX_REC_FOLLOWS = 5

# command line parsing and help menu
def parse_opts():
    if len(sys.argv) == 1: return

    global MAX_LIKES
    global MAX_REC_FOLLOWS
    global SESS_FILE
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l:f:s:hn")
        for o, a in opts:
            if o == "-l": MAX_LIKES = int(a)
            elif o == "-f": MAX_REC_FOLLOWS = int(a)
            elif o == "-s": SESS_FILE = str(a)
            elif o == "-h": help()
            else: logf(f"unidentified argument {o}")
    except Exception as e:
        logf(f"failed parsing arguments: {e}")

def help():
    print(f"usage: {sys.argv[0]} [options]")
    print("befriend, an instagram account manager so you don't have to")
    print("\t-l\t\tamount of posts to like on feed")
    print("\t-f\t\tamount of accounts to follow from 'Suggested for you'")
    print("\t-s\t\tsession file to load and save browser data to")
    print("\t-h\t\tdisplay this handy help message")
    sys.exit(0)


# Log messaging
def logf(msg : str):
    log("FAILURE: "+msg)
    sys.exit(1)

def log(msg : str):
    print("{0}: {1}".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        msg
    ), file=sys.stderr)


# add random sleep periods
def wait_small():
    sleep(rand(0.4, 1.1))

def wait_long():
    sleep(rand(4.5, 11))


# load and save context session data
def sess_save(ctx, file_path=SESS_FILE):
    log(f"saving session data to {file_path}...")
    try:
        with open(file_path, "w") as f:
            json.dump(ctx.cookies(), f)
    except Exception as e:
        logf(str(e))

def sess_load(ctx, file_path=SESS_FILE):
    log(f"loading session data from {file_path}...")
    try:
        with open(file_path, "r") as f:
            cookies = json.load(f)
            if not cookies: log("no session data in file")
            else: ctx.add_cookies(cookies)
    except FileNotFoundError as e:
        log(f"session data not loaded: {e}")
    except Exception as e:
        logf(str(e))


# check for login page, login to account if needed
def login(ctx):
    global USERNAME
    global PASSWORD 

    page = ctx.new_page()
    page.goto("https://www.instagram.com/")
    page.wait_for_load_state("networkidle")
    usr = page.get_by_label("Phone number, username, or")
    pwd = page.get_by_label("Password")

    if usr.count() == 1 and pwd.count() == 1:
        log("login page detected")
        if PASSWORD == "": PASSWORD = getpass(f"enter password for {USERNAME}: ")
        print("logging in ...")

        usr.click()
        wait_small()
        usr.fill(USERNAME)
        wait_small()
        pwd.click()
        wait_small()
        pwd.fill(PASSWORD)
        wait_small()

        page.get_by_role("button", name="Log in", exact=True).click()
        wait_long()
        page.wait_for_load_state("networkidle")

        if page.get_by_text("Sorry, your password was").count() > 0:
            page.close()
            logf("incorrect login provided")

        if page.get_by_role("button", name="Save info").count() == 1:
            page.get_by_role("button", name="Save info").click()
            log("saving login info into browser context...")

        wait_long()
        page.wait_for_load_state("networkidle")
    else:
        log("login using session data successful :)")
        
    return page


def scroll_feed(page, mlikes : int):
    log("liking posts in feed...")
    wait_small()
    i = 0
    for _ in range(0, mlikes):
        post_locator = page.locator('article:has([role="button"]:has-text("Like"),'+\
                '[role="button"]:has-text("More options"), [role="button"]:has-text("Save")'+
                '):not(:has-text("Sponsored"))')
        post_like_button = post_locator.get_by_role("button", name="Like", exact=True).first
        post_like_button.scroll_into_view_if_needed()
        page.wait_for_load_state("networkidle")
        post_like_button.click()
        wait_long()
        i += 1
        if i % 5 == 0:
            log(f"liked {i} posts from home feed")
    log(f"liked {i} posts from home feed")


def follow_recs(page, mfollows : int):
    page.get_by_role("link", name="See All", exact=True).click()
    wait_long()
    page.wait_for_load_state("networkidle")

    for i in range(0, mfollows):
        profile = page.locator('div:not(:has-text("Suggested")):has-text("Followed by "):has(._acan:has-text("Follow"))')
        profile.locator('._acan').nth(i).click()
        wait_long()
        reqd = page.locator(f'div:not(:has-text("Suggested")):has-text("Followed by "):has-text("{profile_name}"):has-text("Requested")')
            
    page.get_by_role("link", name="Home Home").click()
    wait_long()
    page.wait_for_load_state("networkidle")


def main():
    global PASSWORD
    global USERNAME

    parse_opts()

    with sync_playwright() as p:
        log("loading browser")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        log("loading session data from save file")
        sess_load(context, SESS_FILE)

        log("following {0} users, liking {1} posts...".format(MAX_REC_FOLLOWS, MAX_LIKES))

        # login to instagram
        page = login(context)
        # follow/request some recommended profiles
        if MAX_REC_FOLLOWS > 0:
            follow_recs(page, MAX_REC_FOLLOWS)
        # scroll feed and like some posts
        if MAX_LIKES > 0:
            scroll_feed(page, MAX_LIKES)

        sess_save(context, SESS_FILE)
        wait_long()
        log("closing page")
        page.close()
    log("done :)")


if __name__ == "__main__":
    main()
