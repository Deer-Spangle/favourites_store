import json
from abc import ABC, abstractmethod

import dateutil
import requests


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
            if new_watch["profile_name"] in self.users:
                if self.users[new_watch["profile_name"]].is_watcher:
                    print(f"New watch: {new_watch['name']} is already a watcher.")
                    continue
                print(f"New watch: Setting {new_watch['name']} as a watcher.")
                self.users[new_watch["profile_name"]].is_watcher = True
            else:
                print(f"New watch: Adding user {new_watch['name']} as a new watcher.")
                new_user = User(new_watch["profile_name"], new_watch["name"], True)
                self.users[new_user.user_id] = new_user
        # Add favourites
        for new_fav in n_data["new_favorites"]:
            if new_fav["profile_name"] not in self.users:
                print(f"New fav: Creating user {new_fav['name']}")
                new_user = User(new_fav["profile_name"], new_fav["name"], False)
                self.users[new_user.user_id] = new_user
            if new_fav["submission_id"] not in self.submissions:
                print(f"New fav: Adding submission {new_fav['submission_name']}")
                new_sub = Submission(new_fav["submission_id"], new_fav["submission_name"])
                self.submissions[new_sub.submission_id] = new_sub
            print(f"New fav: Adding favourite by {new_fav['profile_name']} on {new_fav['submission_name']}")
            fav = Favourite(new_fav["profile_name"], new_fav["submission_id"])
            fav.fav_date = dateutil.parser.parse(new_fav["posted_at"])
            self.favourites.append(fav)


class WeasylSite(Site):

    def update_favourites_and_watchers(self):
        pass  # TODO


class SofurrySite(Site):

    def update_favourites_and_watchers(self):
        pass  # TODO


class InkbunnySite(Site):

    def update_favourites_and_watchers(self):
        pass  # TODO


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
    cookie_a = input("Enter cookie A value: ")
    cookie_b = input("Enter cookie B value: ")
    if cookie_a and cookie_b:
        site.update_favourites_and_watchers(cookie_a=cookie_a, cookie_b=cookie_b)
    else:
        print("Skipping furaffinity update")


if __name__ == "__main__":
    store = FavouriteStore.load_from_json()
    print_default_stats(store)
    for fav_site in store.sites:
        {
            "furaffinity": update_furaffinity
        }[fav_site.name]()
    print(store)


"""
Top ten arts:
Top ten favouriters:
by site
"""
