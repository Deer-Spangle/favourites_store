import json
import re
from abc import ABC, abstractmethod
from datetime import datetime

import dateutil.parser
import requests
from bs4 import BeautifulSoup


class FavouriteStore:
    file_name = "fav_datastore.json"

    def __init__(self):
        self.sites = {}

    def save_to_json(self):
        data = {
            "sites": [
                site.to_json() for site in self.sites
            ]
        }
        with open(self.file_name, "w") as f:
            json.dump(data, f)

    @classmethod
    def load_from_json(cls):
        with open(cls.file_name, "r") as f:
            data = json.load(f)
        fav_store = cls()
        site_cls_lookup = {
            "furaffinity": FuraffinitySite,
            "weasyl": WeasylSite,
            "sofurry": SofurrySite,
            "inkbunny": InkbunnySite
        }
        for site_data in data["sites"]:
            site_name = site_data['name']
            site_class = site_cls_lookup.get(site_name, Site)
            fav_store.sites[site_name] = site_class.from_json(site_data)
        return fav_store


class Site(ABC):

    def __init__(self, name):
        self.name = name
        self.users = {}
        self.submissions = {}
        self.favourites = []

    @abstractmethod
    def update_favourites_and_watchers(self):
        pass

    def get_submission_favourites_index(self):
        index = []
        for submission in self.submissions.values():
            favourites = [fav for fav in self.favourites if fav.submission_id == submission.submission_id]
            sort_entry = {
                "submission": submission,
                "favourites": favourites,
                "fav_count": len(favourites)
            }
            index.append(sort_entry)
        index_sorted = sorted(index, key=lambda x: x["fav_count"], reverse=True)
        return index_sorted

    def get_user_favourites_index(self):
        index = []
        for user in self.users.values():
            favourites = [fav for fav in self.favourites if fav.user_id == user.user_id]
            sort_entry = {
                "user": user,
                "favourites": favourites,
                "fav_count": len(favourites)
            }
            index.append(sort_entry)
        index_sorted = sorted(index, key=lambda x: x["fav_count"], reverse=True)
        return index_sorted

    def mark_watcher(self, user_id, user_name, watch_date=None):
        if user_id not in self.users:
            print(f"New watch: Adding user: {user_name}")
            user = User(user_id, user_name, True)
            user.watch_date = watch_date
            self.users[user_id] = user
        else:
            if self.users[user_id].is_watcher:
                print(f"New watch: {user_name} is already a watcher")
                self.users[user_id].watch_date = watch_date
            else:
                print(f"New watch: Setting {user_name} as a watcher.")
                self.users[user_id].is_watcher = True
                self.users[user_id].watch_date = watch_date

    def mark_favourite(self, user_id, user_name, submission_id, submission_name, fav_date=None):
        if user_id not in self.users:
            print(f"New fav: Adding user: {user_name}")
            user = User(user_id, user_name, False)
            self.users[user_id] = user
        if submission_id not in self.submissions:
            print(f"New fav: Adding submission: {submission_name}")
            submission = Submission(submission_id, submission_name)
            self.submissions[submission_id] = submission
        print(f"New fav: Adding favourite by {user_name} on {submission_name}")
        fav = Favourite(user_id, submission_id)
        fav.fav_date = fav_date
        self.favourites.append(fav)

    def to_json(self):
        return {
            "name": self.name,
            "users": [user.to_json() for user in self.users.values()],
            "submissions": [sub.to_json() for sub in self.submissions.values()],
            "favourites": [fav.to_json() for fav in self.favourites]
        }

    @classmethod
    def from_json(cls, data):
        site = cls(data['name'])
        for user_data in data['users']:
            site.users[user_data['user_id']] = User.from_json(user_data)
        for sub_data in data['submissions']:
            site.submissions[sub_data['submission_id']] = Submission.from_json(sub_data)
        for fav_data in data['favourites']:
            site.favourites.append(Favourite.from_json(fav_data))
        return site


class FuraffinitySite(Site):
    api_url = "https://faexport.spangle.org.uk/"

    def update_favourites_and_watchers(self, cookie_a=None, cookie_b=None):
        notifications_url = f"{self.api_url}/notifications/others.json"
        headers = {"FA_COOKIE": f"b={cookie_b}; a={cookie_a}"}
        resp = requests.get(notifications_url, headers=headers)
        n_data = resp.json()
        total_watch_count = n_data["notification_counts"]["watchers"]
        total_fav_count = n_data["notification_counts"]["favorites"]
        if total_watch_count != len(n_data["new_watches"]):
            print("Can't see all watcher notifications.")
        if total_fav_count != len(n_data["new_favorites"]):
            print("Can't see all favourite notifications.")
        # Add watchers
        for new_watch in n_data["new_watches"]:
            self.mark_watcher(
                new_watch["profile_name"],
                new_watch["name"],
                dateutil.parser.parse(new_watch["posted_at"])
            )
        # Add favourites
        for new_fav in n_data["new_favorites"]:
            self.mark_favourite(
                new_fav["profile_name"],
                new_fav["name"],
                new_fav["submission_id"],
                new_fav["submission_name"],
                dateutil.parser.parse(new_fav["posted_at"])
            )


class WeasylSite(Site):

    def update_favourites_and_watchers(self, wzl=None):
        notifications_url = "https://www.weasyl.com/messages/notifications"
        headers = {"Cookie": f"WZL={wzl}"}
        resp = requests.get(notifications_url, headers=headers)
        soup = BeautifulSoup(resp.content, "html.parser")
        for follower in soup.select("#followers .item"):
            user_id = follower.select_one("a")["href"].lstrip("/~")
            user_name = follower.select_one("a").text
            watch_date = dateutil.parser.parse(follower.select_one(".date").text)
            self.mark_watcher(user_id, user_name, watch_date)
        for favourite in soup.select("#user_favorites .item"):
            fav_links = favourite.select("a")
            user_id = fav_links[0]["href"].lstrip("/~")
            user_name = fav_links[0].text
            submission_id = fav_links[1]["href"].split("/")[2]
            submission_name = fav_links[1].text
            fav_date = dateutil.parser.parse(favourite.select_one(".date").text)
            self.mark_favourite(user_id, user_name, submission_id, submission_name, fav_date)


class SofurrySite(Site):

    def update_favourites_and_watchers(self, phpsessid=None):
        favs_soup = self._get_favourite_notifications(phpsessid)
        for fav in favs_soup:
            self._add_favourite_from_soup(fav)
        watch_soup = self._get_watch_notifications(phpsessid)
        for watch in watch_soup:
            self._add_watch_from_soup(watch)

    def _add_watch_from_soup(self, watch_soup):
        watch_link = watch_soup.select("td a")[0]
        user_id = watch_link["href"].split("://")[-1].split(".")[0]
        user_name = watch_link["title"]
        watch_date = dateutil.parser.parse(watch_soup.select("td")[3].text)
        self.mark_watcher(user_id, user_name, watch_date)

    def _add_favourite_from_soup(self, fav_soup):
        fav_links = fav_soup.select("td a")
        user_id = fav_links[0]["href"].split("://")[-1].split(".")[0]
        user_name = fav_links[0]["title"]
        submission_id = fav_links[1]["href"].split("/")[-1]
        submission_name = fav_links[1].text
        fav_date = dateutil.parser.parse(fav_soup.select("td")[4].text)
        self.mark_favourite(user_id, user_name, submission_id, submission_name, fav_date)

    def _get_watch_notifications(self, phpsessid):
        url_base = "https://www.sofurry.com/user/notification/listWatches?Notification_page={page}"
        print("Searching watch notifications")
        return self._get_notifications(phpsessid, url_base)

    def _get_favourite_notifications(self, phpsessid):
        url_base = "https://www.sofurry.com/user/notification/listFavorites?Notification_page={page}"
        print("Searching favourite notifications")
        return self._get_notifications(phpsessid, url_base)

    # noinspection PyMethodMayBeStatic
    def _get_notifications(self, phpsessid, url_pattern):
        page = 1
        notifications = []
        while page < 100:
            url = url_pattern.format(page=page)
            page += 1
            resp = requests.get(url, headers={"Cookie": f"PHPSESSID={phpsessid}"})
            soup = BeautifulSoup(resp.content, "html.parser")
            summary = soup.select_one("#yw0 .summary")
            if summary is None:
                print("No notifications")
                return []
            new_favs = soup.select("#yw0 .items tbody tr")
            notifications += new_favs
            if re.search(r"Displaying \d+-(\d+) of \1 result\(s\).", summary.text):
                return notifications
        print("Too many pages of notifications encountered.")
        return notifications


class InkbunnySite(Site):

    def update_favourites_and_watchers(self, phpsessid=None):
        notice_url = "https://inkbunny.net/portal.php"
        headers = {"Cookie": f"PHPSESSID={phpsessid}"}
        resp = requests.get(notice_url, headers=headers)
        soup = BeautifulSoup(resp.content, "html.parser")
        for favourite in soup.select(".up_noticebox_favorites"):
            user_link = favourite.select_one("a.widget_userNameSmall")
            user_id = user_link["href"][1:]
            user_name = user_link.text
            submission_id = favourite.select_one(".widget_imageFromSubmission a")["href"].lstrip("/s")
            submission_alt = favourite.select_one(".widget_imageFromSubmission img")["alt"]
            submission_name = " ".join(submission_alt.split(" ")[:-2])
            fav_date_id = favourite.select_one(".searchfor_timeblocks")["id"] + "_epochtime"
            fav_date = datetime.utcfromtimestamp(int(favourite.select_one("#" + fav_date_id).text))
            self.mark_favourite(user_id, user_name, submission_id, submission_name, fav_date)
        for watch in soup.select(".up_noticebox_watches"):
            user_link = watch.select_one("a.widget_userNameSmall")
            user_id = user_link["href"][1:]
            user_name = user_link.text
            watch_date_id = watch.select_one(".searchfor_timeblocks")["id"] + "_epochtime"
            watch_date = datetime.utcfromtimestamp(int(watch.select_one("#" + watch_date_id).text))
            self.mark_watcher(user_id, user_name, watch_date)


class User:

    def __init__(self, user_id, name, is_watcher):
        self.user_id = user_id
        self.name = name
        self.is_watcher = is_watcher
        self.watch_date = None

    def to_json(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "is_watcher": self.is_watcher,
            "watch_date": self.watch_date.isoformat() if self.watch_date else None
        }

    @classmethod
    def from_json(cls, data):
        user = cls(data['user_id'], data['name'], data['is_watcher'])
        watch_date_str = data.get("watch_date")
        if watch_date_str:
            user.watch_date = dateutil.parser.parse(watch_date_str)
        return user


class Submission:

    def __init__(self, submission_id, title):
        self.submission_id = submission_id
        self.title = title
        self.upload_date = None

    def to_json(self):
        return {
            "submission_id": self.submission_id,
            "title": self.title,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None
        }

    @classmethod
    def from_json(cls, data):
        sub = cls(data['submission_id'], data['title'])
        upload_date_str = data.get("upload_date")
        if upload_date_str:
            sub.upload_date = dateutil.parser.parse(upload_date_str)
        return sub


class Favourite:

    def __init__(self, user_id, submission_id):
        self.user_id = user_id
        self.submission_id = submission_id
        self.fav_date = None

    def to_json(self):
        return {
            "user_id": self.user_id,
            "submission_id": self.submission_id,
            "fav_date": self.fav_date.isoformat() if self.fav_date else None
        }

    @classmethod
    def from_json(cls, data):
        fav = cls(data['user_id'], data['submission_id'])
        fav_date_str = data.get("fav_date")
        if fav_date_str:
            fav.fav_date = dateutil.parser.parse(fav_date_str)
        return fav


def print_default_stats(fav_store):
    for site in fav_store.sites.values():
        print_site(site)
        print("-" * 40)


def print_site(site):
    print(f"Site: {site.name}")
    print("Top 10 submissions")
    top_submissions = site.get_submission_favourites_index()
    for x in range(min(10, len(top_submissions))):
        submission = top_submissions[x]
        print(f"{submission['fav_count']} favs: {submission['submission'].title}")
    print("-" * 20)
    print("Top 10 users")
    top_users = site.get_user_favourites_index()
    for x in range(min(10, len(top_users))):
        user = top_users[x]
        print(f"{user['fav_count']} favs: {user['user'].name}")


def update_furaffinity(site):
    print("Updating furaffinity from notifications")
    cookie_a = input("Enter cookie A value: ")
    cookie_b = input("Enter cookie B value: ")
    if cookie_a and cookie_b:
        try:
            site.update_favourites_and_watchers(cookie_a=cookie_a, cookie_b=cookie_b)
        except Exception as e:
            print(f"Failed to update furaffinity due to failure: {e}")
    else:
        print("Skipping furaffinity update")


def update_sofurry(site):
    print("Updating sofurry from notifications")
    phpsessid = input("Enter cookie PHPSESSID value: ")
    if phpsessid:
        try:
            site.update_favourites_and_watchers(phpsessid=phpsessid)
        except Exception as e:
            print(f"Failed to update sofurry due to failure: {e}")
    else:
        print("Skipping sofurry update")


def update_weasyl(site):
    print("Updating weasyl from notifications")
    wzl = input("Enter cookie WZL value: ")
    if wzl:
        try:
            site.update_favourites_and_watchers(wzl=wzl)
        except Exception as e:
            print(f"Failed to update weasyl due to failure: {e}")
    else:
        print("Skipping weasyl update")


def update_inkbunny(site):
    print("Updating inkbunny from notifications")
    phpsessid = input("Enter cookie PHPSESSID for inkbunny: ")
    if phpsessid:
        try:
            site.update_favourites_and_watchers(phpsessid=phpsessid)
        except Exception as e:
            print(f"Failed to update inkbunny due to failure: {e}")
    else:
        print("Skipping inkbunny update")


if __name__ == "__main__":
    store = FavouriteStore.load_from_json()
    print_default_stats(store)
    for fav_site in store.sites.values():
        {
            "furaffinity": update_furaffinity,
            "sofurry": update_sofurry,
            "weasyl": update_weasyl,
            "inkbunny": update_inkbunny
        }[fav_site.name](fav_site)
    print(store)
