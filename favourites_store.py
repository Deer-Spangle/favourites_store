import json
from abc import ABC, abstractmethod

import dateutil


class Datastore:
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
        store = cls()
        site_cls_lookup = {
            "furaffinity": FuraffinitySite,
            "weasyl": Site,  # TODO
            "sofurry": Site,  # TODO
            "inkbunny": Site  # TODO
        }
        for site_data in data["sites"]:
            site_name = site_data['name']
            site_class = site_cls_lookup.get(site_name, Site)
            store.sites[site_name] = site_class.from_json(site_data)
        return store


class Site(ABC):

    def __init__(self, name):
        self.name = name
        self.users = {}
        self.submissions = {}
        self.favourites = []

    @abstractmethod
    def update_favourites_and_watchers(self):
        pass

    def get_top_submissions(self, count=10):
        pass

    def get_top_users(self, count=10):
        pass

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

    def update_favourites_and_watchers(self):
        pass


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


if __name__ == "__main__":
    datastore = Datastore.load_from_json()
    print(datastore)


"""
Top ten arts:
Top ten favouriters:
by site
"""