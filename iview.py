#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_xml, grab_json, download_rtmp, Node
from datetime import datetime

BASE_URL = "http://www.abc.net.au/iview/"
CONFIG_URL = BASE_URL + "xml/config.xml"
HASH_URL = BASE_URL + "images/iview.jpg"
NS = {
	"auth": "http://www.abc.net.au/iView/Services/iViewHandshaker",
}

class IviewNode(Node):
	def __init__(self, title, parent, vpath):
		Node.__init__(self, title, parent)
		self.vpath = vpath
		self.can_download = True
	
	def download(self):
		auth_doc = grab_xml(PARAMS["auth"], 0)
		vbase = auth_doc.xpath("//auth:server/text()", namespaces=NS)[0]
		token = auth_doc.xpath("//auth:token/text()", namespaces=NS)[0]
		vbase += "?auth=" + token
		vpath, ext = self.vpath.rsplit(".", 1)
		vpath = ext + ":" + vpath
		filename = self.title + "." + ext
		return download_rtmp(filename, vbase, vpath, HASH_URL)
	

def fill_nodes(root_node):
	config_doc = grab_xml(CONFIG_URL, 24*3600)
	global PARAMS
	PARAMS = dict((p.attrib["name"], p.attrib["value"]) for p in config_doc.xpath("/config/param"))

	categories_doc = grab_xml(BASE_URL + PARAMS["categories"], 24*3600)
	categories_map = {}
	for category in categories_doc.xpath("//category[@genre='true']"):
		cid = category.attrib["id"]
		category_name = category.xpath("name/text()")[0]
		category_node = Node(category_name, root_node)
		categories_map[cid] = category_node

	# Create a duplicate of each series within each category that it appears
	series_list_doc = grab_json(PARAMS["api"] + "seriesIndex", 3600)
	now = datetime.now()
	for series in series_list_doc:
		categories = series["e"].split()
		sid = series["a"]
		max_age = None
		for episode in series["f"]:
			air_date = datetime.strptime(episode["f"], "%Y-%m-%d %H:%M:%S")
			diff = now - air_date
			diff = 24*3600*diff.days + diff.seconds
			if max_age is None or diff < max_age:
				max_age = diff

		if max_age is None:
			continue

		series_title = series["b"].replace("&amp;", "&")
		series_nodes = []
		for cid in categories:
			category_node = categories_map.get(cid, None)
			if category_node:
				series_nodes.append(Node(series_title, category_node))
		if not series_nodes:
			continue

		series_doc = grab_json(PARAMS["api"] + "series=" + sid, max_age)[0]
		for episode in series_doc["f"]:
			vpath = episode["n"]
			episode_title = episode["b"].strip()
			if series_title != episode_title:
				episode_title = series_title + " " + episode_title
			for series_node in series_nodes:
				IviewNode(episode_title, series_node, vpath)


