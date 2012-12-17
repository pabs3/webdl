#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import append_to_qs, grab_xml, grab_json, download_rtmp, Node
from datetime import datetime

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
		vbase = auth_doc.xpath("//auth:server/text()", namespaces=NS)[0]
		token = auth_doc.xpath("//auth:token/text()", namespaces=NS)[0]
		vbase = append_to_qs(vbase, {"auth": token})
		vpath, ext = self.vpath.rsplit(".", 1)
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

class IviewRootNode(Node):
	def __init__(self, parent):
		Node.__init__(self, "ABC iView", parent)

	def fill_children(self):
		config_doc = grab_xml(CONFIG_URL, 24*3600)
		params = dict((p.attrib["name"], p.attrib["value"]) for p in config_doc.xpath("/config/param"))

		categories_doc = grab_xml(BASE_URL + params["categories"], 24*3600)
		categories_map = {}
		for category in categories_doc.xpath("//category[@genre='true']"):
			cid = category.attrib["id"]
			category_name = category.xpath("name/text()")[0]
			category_node = Node(category_name, self)
			categories_map[cid] = category_node

		# Create a duplicate of each series within each category that it appears
		series_list_doc = grab_json(params["api"] + "seriesIndex", 3600)
		for series in series_list_doc:
			categories = series["e"].split()
			sid = series["a"]

			series_title = series["b"].replace("&amp;", "&")
			for cid in categories:
				category_node = categories_map.get(cid, None)
				if category_node:
					IviewSeriesNode(series_title, category_node, params, sid)



def fill_nodes(root_node):
	IviewRootNode(root_node)

