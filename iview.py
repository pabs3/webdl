#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_xml, grab_json, download_rtmp, Node
from datetime import datetime
import itertools

BASE_URL = "http://www.abc.net.au/iview/"
CONFIG_URL = BASE_URL + "xml/config.xml"
HASH_URL = BASE_URL + "images/iview.jpg"
NS = {
	"auth": "http://www.abc.net.au/iView/Services/iViewHandshaker",
}

class IviewNode(Node):
	def __init__(self, title, parent, params, vpath):
		Node.__init__(self, title, parent)
		self.params = params
		self.vpath = vpath
		self.can_download = True

	def download(self):
		auth_doc = grab_xml(self.params["auth"], 0)
###		vbase = auth_doc.xpath("//auth:server/text()", namespaces=NS)[0]
		token = auth_doc.xpath("//auth:token/text()", namespaces=NS)[0]
		vbase = "rtmp://cp53909.edgefcs.net/ondemand"
		vbase += "?auth=" + token
		vpath, ext = self.vpath.rsplit(".", 1)
		vpath = "flash/playback/_definst_/" + vpath
		vpath = ext + ":" + vpath
		filename = self.title + "." + ext
		return download_rtmp(filename, vbase, vpath, HASH_URL)


class IviewSeriesNode(Node):
	def __init__(self, title, parent, params, series_id):
		Node.__init__(self, title, parent)
		self.params = params
		self.series_id = series_id

	def fill_children(self):
		series_doc = grab_json(self.params["api"] + "series=" + self.series_id, 3600)
		if not series_doc:
			return
		for episode in series_doc[0]["f"]:
			vpath = episode["n"]
			episode_title = episode["b"].strip()
			if not episode_title.startswith(self.title):
				episode_title = self.title + " " + episode_title
			if episode_title.lower().endswith(" (final)"):
				episode_title = episode_title[:-8]
			IviewNode(episode_title, self, self.params, vpath)

class SeriesInfo(object):
	def __init__(self, title, sid, categories):
		self.title = title
		self.sid = sid
		self.categories = categories

class IviewRootNode(Node):
	def __init__(self, parent):
		Node.__init__(self, "ABC iView", parent)
		self.params = {}
		self.series_info = []
		self.categories_map = {}

	def load_params(self):
		config_doc = grab_xml(CONFIG_URL, 24*3600)
		for p in config_doc.xpath("/config/param"):
			key = p.attrib["name"]
			value = p.attrib["value"]
			self.params[key] = value

	def load_series(self):
		series_list_doc = grab_json(self.params["api"] + "seriesIndex", 3600)
		for series in series_list_doc:
			title = series["b"].replace("&amp;", "&")
			sid = series["a"]
			categories = series["e"].split()
			info = SeriesInfo(title, sid, categories)
			self.series_info.append(info)

	def load_categories(self):
		categories_doc = grab_xml(BASE_URL + self.params["categories"], 24*3600)
		by_channel = Node("By Channel", self)
		by_genre = Node("By Genre", self)
		for category in categories_doc.xpath("//category"):
			cid = category.attrib["id"]
			category_name = category.xpath("name/text()")[0]
			if "genre" in category.attrib:
				parent = by_genre
			elif cid in ["abc1", "abc2", "abc3", "abc4", "original"]:
				parent = by_channel
			elif cid in ["featured", "recent", "last-chance", "trailers"]:
				parent = self
			else:
				continue
			node = Node(category_name, parent)
			self.categories_map[cid] = node

	def link_series(self):
		# Create a duplicate within each category for each series
		for s in self.series_info:
			for cid in s.categories:
				parent = self.categories_map.get(cid)
				if parent:
					IviewSeriesNode(s.title, parent, self.params, s.sid)

	def fill_children(self):
		self.load_params()
		self.load_series()
		self.load_categories()
		self.link_series()


def fill_nodes(root_node):
	IviewRootNode(root_node)

