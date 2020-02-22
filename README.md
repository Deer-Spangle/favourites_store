# Favourites store
This project is just a simple store of favourites information for different furry sites.

It's a command line tool, which can scrape notification data for new watchers and favourites, and store them in a json file.

It can then tell you the submissions which have received the most favourites, and the users who've favourited the most of your submissions.

It can currently scrape notifications from:
- Furaffinity (Only the first 30 which are displayed, after that you will need to delete some, and run the scan again)
- SoFurry
- Weasyl

And in the future it shall be able to scan:
- Inkbunny

To do these scans, you will need to pass in some cookie values from the command line. You can get these by using the storage inspector in firefox or chrome.