#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

import json
import random
import string
import urllib
from lxml.cssselect import CSSSelector

from common import grab_html, grab_json, download_rtmp, Node

BASE = "http://au.tv.yahoo.com"
BROWSE = BASE + "/plus7/browse/"

METADATA_BASE = "http://video.query.yahoo.com/v1/public/yql?"
METADATA_QUERY = {
	'q': 'SELECT streams,status FROM yahoo.media.video.streams WHERE id="%s" AND format="mp4,flv" AND protocol="rtmp,http" AND plrs="%s" AND offnetwork="false" AND site="autv_plus7" AND lang="en-AU" AND region="AU" AND override="none";',
	'callback': 'jsonp_callback',
	'env': 'prod',
	'format': 'json'
}

HASH_URL = "http://d.yimg.com/m/up/ypp/au/player.swf"


def extract_and_remove(tokens, key):
	lowertokens = [x.lower() for x in tokens]
	pos = lowertokens.index(key)

	value = int(tokens[pos+1])
	tokens = tokens[:pos] + tokens[pos+2:]

	return value, tokens


def demangle_title(title, subtitle):
	tokens = title.split()
	insert_pos = len(tokens)
	if subtitle:
		insert_pos += 1
		tokens += ["-"] + subtitle.split()

	try:
		season, tokens = extract_and_remove(tokens, "series")
		episode, tokens = extract_and_remove(tokens, "episode")
		if insert_pos < len(tokens):
			tokens.insert(insert_pos, "-")
		tokens.insert(insert_pos, "%sx%s" % (season, str(episode).zfill(2)))
	except ValueError:
		pass

	return " ".join(tokens)

class Plus7Node(Node):
	def __init__(self, title, parent, url):
		Node.__init__(self, title, parent)
		self.url = url
		self.can_download = True
	
	def get_video_id(self):
		doc = grab_html(self.url, 3600)
		for script in doc.xpath("//script"):
			if not script.text:
				continue
			for line in script.text.split(";"):
				line = line.strip()
				if line.find("new Y.VideoPlatform.VideoPlayer") <= 0:
					continue

###				vidparams = line[line.find("(")+1 : line.rfind(")")]
###				vidparams = json.loads(vidparams)
###				return vidparams["playlist"]["mediaItems"][0]["id"]

				# Cannot parse it as JSON :(
				pos1 = line.find('"mediaItems":')
				if pos1 < 0:
					continue
				pos2 = line.find('"id":', pos1)
				if pos2 < 0:
					continue
				pos3 = line.find('"', pos2+5)
				pos4 = line.find('"', pos2+6)
				if pos3 < 0 or pos4 < 0:
					continue
				return line[pos3+1:pos4]

		raise Exception("Could not find video id on page " + self.url)

	def generate_session(self):
		return "".join([random.choice(string.ascii_letters) for x in xrange(22)])

	def download(self):
		vid_id = self.get_video_id()
		qs = dict(METADATA_QUERY.items()) # copy..
		qs["q"] = qs["q"] % (vid_id, self.generate_session())
		url = METADATA_BASE + urllib.urlencode(qs)
		doc = grab_json(url, 0, skip_function=True)
		stream_data = doc["query"]["results"]["mediaObj"][0]["streams"][0]
		vbase = stream_data["host"]
		vpath = stream_data["path"]
		filename = self.title + ".flv"
		return download_rtmp(filename, vbase, vpath, HASH_URL)


class Plus7Series(Node):
	def __init__(self, title, parent, url):
		Node.__init__(self, title, parent)
		self.url = url

	def fill_children(self):
		doc = grab_html(self.url, 3600)
		for item in CSSSelector("#related-episodes div.itemdetails")(doc):
			title = CSSSelector("span.title")(item)[0].text
			subtitle = CSSSelector("span.subtitle")(item)[0].xpath("string()")
			title = demangle_title(title, subtitle)
			url = CSSSelector("a")(item)[0].attrib["href"]
			Plus7Node(title, self, BASE + url)

class Plus7Root(Node):
	def __init__(self, parent):
		Node.__init__(self, "Yahoo Plus7", parent)

	def fill_children(self):
		doc = grab_html(BROWSE, 3600)
		shows = []
		for script in doc.xpath("//script"):
			if not script.text or not script.text.startswith("var shows = "):
				continue
			shows = script.text[12:]
			shows = shows.rstrip("; \n")
			shows = json.loads(shows)
		for show in shows:
			Plus7Series(show["title"], self, show["url"])

def fill_nodes(root_node):
	Plus7Root(root_node)

