#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_html, grab_json, grab_xml, download_rtmp, download_urllib, Node, append_to_qs

import collections
import urlparse

BASE = "http://www.sbs.com.au"
VIDEO_MENU = BASE + "/ondemand/js/video-menu"
VIDEO_URL = BASE + "/ondemand/video/single/%s"
VIDEO_MAGIC = {
	"v": "2.5.14",
	"fp": "MAC 11,1,102,55",
	"r": "FLQDD",
	"g": "YNANAXRIYFYO",
}
SWF_URL = "http://resources.sbs.com.au/vod/theplatform/core/current/swf/flvPlayer.swf"

NS = {
	"smil": "http://www.w3.org/2005/SMIL21/Language",
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

		desc_url = append_to_qs(desc_url, {"manifest": None})
		doc = grab_xml(desc_url, 0)
		video = doc.xpath("//smil:video", namespaces=NS)[0]
		video_url = video.attrib["src"]
		ext = urlparse.urlsplit(video_url).path.rsplit(".", 1)[1]
		filename = self.title + "." + ext
		video_url = append_to_qs(video_url, VIDEO_MAGIC)
		print video_url
		return download_urllib(filename, video_url, referrer=SWF_URL)

class SbsNavNode(Node):
	def __init__(self, title, parent, url):
		Node.__init__(self, title, parent)
		self.url = url
		self.sort_children = True

	def fill_children(self):
		try:
			doc = grab_json(BASE + self.url, 3600)
		except ValueError:
			# SBS sends XML as an error message :\
			return
		if len(doc.get("entries", [])) == 0:
			return
		for entry in doc["entries"]:
			self.fill_entry(entry)

	def fill_entry(self, entry):
		title = entry["title"]
		video_id = entry["id"]
		SbsNode(title, self, video_id)

class SbsRootNode(Node):
	def __init__(self, parent=None):
		Node.__init__(self, "SBS", parent)

	def fill_children(self):
		menu = grab_json(VIDEO_MENU, 3600, skip_assignment=True)
		for name in menu.keys():
			self.fill_category(self, menu[name])

	def create_nav_node(self, name, parent, cat_data, url_key):
		try:
			url = cat_data[url_key]
		except KeyError:
			return
		if url.strip():
			SbsNavNode(name, parent, url)

	def fill_category(self, parent, cat_data):
		if not cat_data.has_key("children"):
			name = cat_data["name"]
			self.create_nav_node(name, parent, cat_data, "url")
			return

		node = Node(cat_data["name"], parent)
		self.create_nav_node("Featured", node, cat_data, "furl")
		self.create_nav_node("Latest", node, cat_data, "url")
		self.create_nav_node("Most Popular", node, cat_data, "purl")

		children = cat_data.get("children", [])
		if isinstance(children, dict):
			children = [children[k] for k in sorted(children.keys())]
		for child_cat in children:
			self.fill_category(node, child_cat)

def fill_nodes(root_node):
	SbsRootNode(root_node)

