#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

import json
from lxml.cssselect import CSSSelector

from common import grab_html, download_rtmp, Node

METADATA = "http://cosmos.bcst.yahoo.com/rest/v2/pops;id=%d;lmsoverride=1;element=stream;bw=1200"
BASE = "http://au.tv.yahoo.com"
BROWSE = BASE + "/plus7/browse/"
HASH_URL = "http://d.yimg.com/nl/australia/au-tv/player.swf"
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
		tokens.insert(insert_pos, "%sx%s -" % (season, str(episode).zfill(2)))
	except ValueError:
		pass

	return " ".join(tokens)

class Plus7Node(Node):
	def __init__(self, title, parent, url):
		Node.__init__(self, title, parent)
		self.url = url
		self.can_download = True
	
	def get_vid(self):
		doc = grab_html(self.url, 3600)
		for script in doc.xpath("//script"):
			if not script.text:
				continue
			for line in script.text.split("\n"):
				if line.find("vid : ") <= 0:
					continue
				vid = line[line.find("'")+1 : line.rfind("'")]
				vid = int(vid)
				return vid
		raise Exception("Could not find vid on page " + self.url)

	def download(self):
		vid = self.get_vid()
		doc = grab_html(METADATA % vid, 0)
		content = doc.xpath("//content")[0]
		vbase = content.attrib["url"]
		vpath = content.attrib["path"]
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
	def __init__(self, parent=None):
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

