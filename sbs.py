#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_json, grab_xml, download_rtmp, download_urllib, Node

import collections

BASE = "http://www.sbs.com.au"
MENU_URL = "/api/video_feed/f/dYtmxB/%s?startIndex=%d"
VIDEO_URL = BASE + "/api/video_feed/f/dYtmxB/CxeOeDELXKEv/%s?form=json"

NS = {
	"smil": "http://www.w3.org/2005/SMIL21/Language",
}

SECTIONS = [
	"section-sbstv",
	"section-programs",
]

CATEGORY_MAP = {
	"Factual": "Documentary",
}


class SbsNode(Node):
	def __init__(self, title, parent, video_id):
		Node.__init__(self, title, parent)
		self.title = title
		self.video_id = video_id.split("/")[-1]
		self.can_download = True

	def download(self):
		doc = grab_json(VIDEO_URL % self.video_id, 0)
		best_url = None
		best_bitrate = 0
		for d in doc["media$content"]:
			bitrate = d["plfile$bitrate"]
			if bitrate > best_bitrate or best_url is None:
				best_bitrate = bitrate
				best_url = d["plfile$url"]

		doc = grab_xml(best_url, 3600)
		if doc.xpath("//smil:meta/@base", namespaces=NS):
			vbase = doc.xpath("//smil:meta/@base", namespaces=NS)[0]
			vpath = doc.xpath("//smil:video/@src", namespaces=NS)[0]
			ext = vpath.rsplit(".", 1)[1]
			filename = self.title + "." + ext
			return download_rtmp(filename, vbase, vpath)
		else:
			from lxml import etree
			url = doc.xpath("//smil:video/@src", namespaces=NS)[0]
			ext = url.rsplit(".", 1)[1]
			filename = self.title + "." + ext
			url += "?v=2.5.14&fp=MAC%2011,1,102,55&r=FLQDD&g=YNANAXRIYFYO"
			return download_urllib(filename, url)

def fill_entry(get_catnode, entry):
	title = entry["title"]
	video_id = entry["id"]
	info = collections.defaultdict(list)
	for d in entry["media$categories"]:
		if not d.has_key("media$scheme"):
			continue
		info[d["media$scheme"]].append(d["media$name"])

	if "Section/Promos" in info.get("Section", []):
		# ignore promos
		return

	for category in info.get("Genre", ["$UnknownCategory$"]):
		category = CATEGORY_MAP.get(category, category)
		parent_node = get_catnode(category)
		SbsNode(title, parent_node, video_id)


def fill_section(get_catnode, section):
	index = 1
	while True:
		doc = grab_json(BASE + MENU_URL % (section, index), 3600)
		if len(doc.get("entries", [])) == 0:
			break
		for entry in doc["entries"]:
			fill_entry(get_catnode, entry)
		index += doc["itemsPerPage"]

class SbsRoot(Node):
	def __init__(self, parent=None):
		Node.__init__(self, "SBS", parent)
		self.catnodes = {}

	def get_catnode(self, name):
		try:
			return self.catnodes[name]
		except KeyError:
			n = Node(name, self)
			self.catnodes[name] = n
			return n

	def fill_children(self):
		for section in SECTIONS:
			fill_section(self.get_catnode, section)

def fill_nodes(root_node):
	SbsRoot(root_node)

