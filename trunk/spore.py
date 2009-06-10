import urllib, datetime
from xml.dom import minidom

serverString = "http://www.spore.com"
achievements = None

class ServerError(Exception):
    pass

def _xmlUrlToDict(url, f=lambda a: a):
    doc = minidom.parse(urllib.urlopen(url))
    d = {}
    for element in doc.firstChild.childNodes:
        if element.nodeType != minidom.Node.ELEMENT_NODE:
            continue
        if element.firstChild == None:
            continue
        if element.tagName == "status":
            if int(element.firstChild.data) != 1:
                raise ServerError(element.firstChild.data)
            continue
        if element.tagName == "input":
            continue
        d[element.tagName] = f(element.firstChild.data)
    return d

def loadAchievementList():
    """Look up the official Spore achievement name and text
Call before getting any achievements"""
    global achievements
    achievements = {}
    doc = minidom.parse(urllib.urlopen(serverString + "/data/achievements.xml"))
    for element in doc.getElementsByTagName("achievement"):
        key = element.getElementsByTagName("id")[0].firstChild.data
        name = element.getElementsByTagName("name")[0].firstChild.data
        description = element.getElementsByTagName("description")[0].firstChild.data
        achievements[key] = (name, description)

def getServerStats():
    """Get daily stats about Spore.com"""
    return _xmlUrlToDict(serverString + "/rest/stats", int)

class Achievement:
    """Stores a user's achievement (id, name, date, description)"""
    def __init__(self, guid=None, date=None, name=None, description=None):
        self.id = guid
        self.date = date
        if name:
            self.name = name
        if description:
            self.description = description
        if guid and achievements and not (name or description):
            self.getInfo()
    def __repr__(self):
        return "Achievement(guid=%r, date=%r, name=%r, description=%r)" % (self.id, self.date, self.name, self.description)
    def getInfo(self):
        """Store name and description (must have loadAchievementList called first)"""
        self.name, self.description = achievements[self.id]
    def getIconUrl(self):
        """Returns the URL for the official Spore achievement icon"""
        return "%s/static/war/images/achievements/%s.png" % (serverString, self.id)

class Author:
    """Stores information about a user"""
    def __init__(self, name=None, id=None):
        self.name = name
        self.id = id
        self.assets = []
        self.achievements = []
        self.buddies = []
    def __repr__(self):
        return "Author(name=%r, id=%r)" % (self.name, self.id)
    def getProfileInfo(self):
        """Get profile pic, tagline, user id and creation date"""
        doc = minidom.parse(urllib.urlopen(serverString + "/rest/user/" + self.name))
        for element in doc.getElementsByTagName("user")[0].childNodes:
            if element.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            elif element.tagName == "status" and int(element.firstChild.data) != 1:
                raise ServerError(element.firstChild.data)
            elif element.tagName == "input":
                self.name = element.firstChild.data
            elif element.tagName == "id":
                self.id = element.firstChild.data
            elif element.tagName == "image":
                self.image = element.firstChild.data
            elif element.tagName == "tagline":
                if element.firstChild == None:
                    self.tagline = None
                else:
                    self.tagline = element.firstChild.data
            elif element.tagName == "creation":
                self.created = datetime.datetime.strptime(element.firstChild.data[:element.firstChild.data.rfind(".")]+".GMT", "%Y-%m-%d %H:%M:%S.%Z")
    def getAssets(self, start=None, length=20):
        """Get asset id, name, creation date, type, parent and rating for a list of assets created by the user"""
        if start == None:
            start = len(self.assets)
        doc = minidom.parse(urllib.urlopen("%s/rest/assets/user/%s/%i/%i" % (serverString, self.name, start, length)))
        if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
            raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
        for element in doc.getElementsByTagName("asset"):
            self.assets += [Asset()]
            self.assets[-1]._getInfoFromNode(element)
    def getAchievements(self, start=None, length=5):
        """Get number of achievements for the user and a list of achievement ids and unlock-dates"""
        if start == None:
            start = len(self.achievements)
        doc = minidom.parse(urllib.urlopen("%s/rest/achievements/%s/%i/%i" % (serverString, self.name, start, length)))
        if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
            raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
        for element in doc.getElementsByTagName("achievement"):
            guid = element.getElementsByTagName("guid")[0].firstChild.data
            date = element.getElementsByTagName("date")[0].firstChild.data
            date = datetime.datetime.strptime(date[:date.rfind(".")]+".GMT", "%Y-%m-%d %H:%M:%S.%Z")
            self.achievements += [Achievement(guid, date)]
    def getBuddies(self, start=None, length=10):
        """Get a list of buddy names and ids and total buddy count for the user"""
        if start == None:
            start = len(self.achievements)
        doc = minidom.parse(urllib.urlopen("%s/rest/users/buddies/%s/%i/%i" % (serverString, self.name, start, length)))
        if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
            raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
        for element in doc.getElementsByTagName("buddy"):
            name = element.getElementsByTagName("name")[0].firstChild.data
            id = element.getElementsByTagName("id")[0].firstChild.data
            self.buddies += [Author(name, id)]

class Comment:
    """Stores information on a comment on a creation"""
    def __init__(self, message=None, sender=None, date=None):
        self.message = message
        if isinstance(sender, basestring):
            self.sender = Author(name=sender)
        else:
            self.sender = sender
        self.date = date
    def __repr__(self):
        return "Comment(message=%r, sender=%r, date=%r)" % (self.message, self.sender, self.date)

class Asset:
    """Stores information about an asset"""
    def __init__(self, assetId=None):
        self.comments = []
        self.id = str(assetId)
        self.type = None
    def __repr__(self):
        return "Asset(%r)" % self.id
    def getInfo(self):
        """Get name, description, tags, 10 latest comments, type, parent, rating, creation date and author name/id"""
        doc = minidom.parse(urllib.urlopen(serverString + "/rest/asset/" + self.id))
        self._getInfoFromNode(doc.getElementsByTagName("asset")[0])
    def _getInfoFromNode(self, node):
        self.author = None
        for element in node.childNodes:
            if element.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            elif element.tagName == "status" and int(element.firstChild.data) != 1:
                raise ServerError(element.firstChild.data)
            elif element.tagName in ("input", "id"):
                self.id = element.firstChild.data
            elif element.tagName == "name":
                self.name = element.firstChild.data
            elif element.tagName == "thumb":
                self.thumb = element.firstChild.data
            elif element.tagName == "image":
                self.image = element.firstChild.data
            elif element.tagName == "author":
                if self.author:
                    self.author.name = element.firstChild.data
                else:
                    self.author = Author(name=element.firstChild.data)
            elif element.tagName == "authorid":
                if self.author:
                    self.author.id = element.firstChild.data
                else:
                    self.author = Author(id=element.firstChild.data)
            elif element.tagName == "created":
                self.created = datetime.datetime.strptime(element.firstChild.data[:element.firstChild.data.rfind(".")]+".GMT", "%Y-%m-%d %H:%M:%S.%Z")
            elif element.tagName == "description":
                if element.firstChild.data == "NULL":
                    self.description = None
                else:
                    self.description = element.firstChild.data
            elif element.tagName == "tags":
                if element.firstChild.data == "NULL":
                    self.tags = []
                else:
                    self.tags = [t.strip() for t in element.firstChild.data.split(",")]
            elif element.tagName == "type":
                self.type = element.firstChild.data
            elif element.tagName == "subtype":
                self.subtype = int(element.firstChild.data, 16)
            elif element.tagName == "rating":
                self.rating = float(element.firstChild.data)
            elif element.tagName == "parent":
                if element.firstChild.data == "NULL":
                    self.parent = None
                else:
                    self.parent = Asset(element.firstChild.data)
            #elif element.tagName == "comments":
            #    self._parseComments(element)
    def _parseComments(self, element):
        for commentNode in element.getElementsByTagName("comment"):
            if commentNode.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            sender = commentNode.getElementsByTagName("sender")[0].firstChild.data
            message = commentNode.getElementsByTagName("message")[0].firstChild.data
            date = commentNode.getElementsByTagName("date")
            date = date[0].firstChild.data
            date = datetime.datetime.strptime(date[:date.rfind(".")]+".GMT", "%Y-%m-%d %H:%M:%S.%Z")
            self.comments += [Comment(message, sender, date)]
    def getComments(self, start=None, length=20):
        """Get a list of comments, sender names and comment dates"""
        if start == None:
            start = len(self.comments)
        doc = minidom.parse(urllib.urlopen("%s/rest/comments/%s/%i/%i" % (serverString, self.id, start, length)))
        if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
            raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
        self._parseComments(doc)
    def getStats(self):
        """Get various stats like height, diet, abilities etc. for a creature"""
        if self.type != "CREATURE" and self.type != None:
            return
        self.stats = _xmlUrlToDict(serverString + "/rest/creature/" + self.id, float)
    def getDataUrls(self):
        """Get XML and PNGs for an asset"""
        sub1 = self.id[0:3]
        sub2 = self.id[3:6]
        sub3 = self.id[6:9]
        self.xml = "%s/static/model/%s/%s/%s/%s.xml" % (serverString, sub1, sub2, sub3, self.id)
        self.image = "%s/static/image/%s/%s/%s/%s_lrg.png" % (serverString, sub1, sub2, sub3, self.id)
        self.thumb = "%s/static/thumb/%s/%s/%s/%s.png" % (serverString, sub1, sub2, sub3, self.id)

def specialSearch(searchType, start=0, length=20, assetType=None):
    """List creations for a given view.
View Types are: TOP_RATED, TOP_RATED_NEW, NEWEST, FEATURED, MAXIS_MADE, RANDOM, CUTE_AND_CREEPY
For each asset you get id, name, author, creation date, rating, type and parent.
Optionally, you can specify an asset type.
Asset types are: UFO, CREATURE, BUILDING, VEHICLE"""
    url = "%s/rest/assets/search/%s/%i/%i" % (serverString, searchType, start, length)
    if assetType:
        url += "/"+assetType
    doc = minidom.parse(urllib.urlopen(url))
    if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
        raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
    assets = []
    for element in doc.getElementsByTagName("asset"):
        assets += [Asset()]
        assets[-1]._getInfoFromNode(element)
    return assets

def find(searchTerm, start=0, length=20, assetType=None):
    url = "%s/rest/assets/find/%s/%i/%i" % (serverString, searchTerm, start, length)
    if assetType:
        url += "/"+assetType
    doc = minidom.parse(urllib.urlopen(url))
    if int(doc.getElementsByTagName("status")[0].firstChild.data) != 1:
        raise ServerError(doc.getElementsByTagName("status")[0].firstChild.data)
    assets = []
    for element in doc.getElementsByTagName("asset"):
        assets += [Asset()]
        assets[-1]._getInfoFromNode(element)
    return assets

if __name__ == "__main__":
    from pprint import pprint
    print "Server stats:"
    pprint(getServerStats())
    print "Special search:"
    assets = specialSearch("FEATURED", length=2, assetType="CREATURE")
    pprint(assets)
    asset = assets[0]
    print "Search:"
    assets = find("impiaaa", length=2, assetType="CREATURE")
    pprint(assets)
    print "Creature stats:"
    asset.getStats()
    pprint(asset.stats)
    print "Asset comments:"
    asset.getComments(length=3)
    pprint(asset.comments)
    print "Asset URLs:"
    asset.getDataUrls()
    print "XML:", asset.xml
    print "Thumb:", asset.thumb
    print "Image:", asset.image
    author = asset.author
    print "Author profile info:"
    author.getProfileInfo()
    print "Image:", author.image
    print "Tagline:", author.tagline
    print "Created:", author.created
    print "Author assets:"
    author.getAssets(length=3)
    pprint(author.assets)
    print "Author achievements:"
    loadAchievementList()
    author.getAchievements(length=3)
    pprint(author.achievements)
    print "Achievement URL:", author.achievements[0].getIconUrl()
    print "Author buddies:"
    author.getBuddies(length=3)
    pprint(author.buddies)
