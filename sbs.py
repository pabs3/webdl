#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_html, grab_json, grab_xml, download_rtmp, download_urllib, Node

import collections

BASE = "http://www.sbs.com.au"
MENU_URL = "/api/video_feed/f/dYtmxB/%s?startIndex=%d"
VIDEO_URL = BASE + "/ondemand/video/single/%s"

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
		doc = grab_html(VIDEO_URL % self.video_id, 0)
		desc_url = None
		for script in doc.xpath("//script", namespaces=NS):
            if not script.text:
                continue
            for line in script.text.split("\n"):
                if line.find("player.releaseUrl") < 0:
                    continue
                desc_url = line[line.find("\"")+1 : line.rfind("\"")]
				break
			if desc_url is not None:
				break
		if desc_url is None:
			raise Exception("Failed to get JSON URL for " + self.title)

		doc = grab_xml(desc_url, 0)
		best_url = None
		best_bitrate = 0
		for video in doc.xpath("//smil:video", namespaces=NS):
			bitrate = int(video.attrib["system-bitrate"])
			if best_bitrate == 0 or best_bitrate < bitrate:
				best_bitrate = bitrate
				best_url = video.attrib["src"]

		ext = best_url.rsplit(".", 1)[1]
		filename = self.title + "." + ext
		best_url += "?v=2.5.14&fp=MAC%2011,1,102,55&r=FLQDD&g=YNANAXRIYFYO"
		return download_urllib(filename, best_url)

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

