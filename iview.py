#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_xml, grab_json, download_rtmp, Node
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
		self.filename = self.title + "." + vpath.rsplit(".", 1)[1]
		self.can_download = True

	def download(self):
		auth_doc = grab_xml(self.params["auth"], 0)
		server = self.params["server_streaming"]
		token = auth_doc.xpath("//auth:token/text()", namespaces=NS)[0]
		playpath = auth_doc.xpath("//auth:path/text()", namespaces=NS)[0]
		if playpath == "playback/_definst_/":
			playpath = "flash/" + playpath
		vbase = server + "?auth=" + token
		vpath, ext = self.vpath.rsplit(".", 1)
		vpath = ext + ":" + playpath + vpath
		return download_rtmp(self.filename, vbase, vpath, HASH_URL)

class IviewSeriesNode(Node):
	def __init__(self, title, parent, params, series_ids):
		Node.__init__(self, title, parent)
		self.params = params
		self.series_ids = series_ids

	def fill_children(self):
		for series_id in self.series_ids:
			self.fill_children_for_id(series_id)

	def fill_children_for_id(self, series_id):
		series_doc = grab_json(self.params["api"] + "series=" + series_id, 3600)
		for episode_list in series_doc:
			if episode_list["a"] == series_id:
				episode_list = episode_list["f"]
				break
		else:
			return

		for episode in episode_list:
			vpath = episode["n"]
			episode_title = episode["b"].strip()
			if not episode_title.startswith(self.title):
				episode_title = self.title + " " + episode_title
			if episode_title.lower().endswith(" (final)"):
				episode_title = episode_title[:-8]
			IviewNode(episode_title, self, self.params, vpath)

class SeriesInfo(object):
	def __init__(self, title):
		self.title = title
		self.series_ids = set()
		self.categories = set()

	def add_series_id(self, series_id):
		self.series_ids.add(series_id)

	def add_categories(self, categories):
		self.categories.update(categories)

class IviewRootNode(Node):
	def __init__(self, parent):
		Node.__init__(self, "ABC iView", parent)
		self.params = {}
		self.series_info = {}
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
			info = self.series_info.get(title, None)
			if not info:
				info = SeriesInfo(title)
				self.series_info[title] = info
			info.add_categories(categories)
			info.add_series_id(sid)

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
		for s in self.series_info.itervalues():
			for cid in s.categories:
				parent = self.categories_map.get(cid)
				if parent:
					IviewSeriesNode(s.title, parent, self.params, s.series_ids)

	def fill_children(self):
		self.load_params()
		self.load_series()
		self.load_categories()
		self.link_series()


def fill_nodes(root_node):
	IviewRootNode(root_node)

