#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import grab_xml as _grab_xml, download_rtmp, download_urllib, Node


BASE_URL = "http://player.sbs.com.au"

def grab_xml(path, max_age):
	return _grab_xml(BASE_URL + path, max_age)

class SbsNode(Node):
	def __init__(self, title, parent, video_desc_url):
		Node.__init__(self, title, parent)
		self.video_desc_url = video_desc_url
		self.can_download = True

	def download(self):
		video = grab_xml(self.video_desc_url, 0)
		vbase = video.xpath("//meta/@base")[0]
		bestrate = 0
		bestvpath = None
		for vpath in video.xpath("//switch/video"):
			rate = float(vpath.xpath("@system-bitrate")[0])
			if rate > bestrate:
				bestrate = rate
				bestvpath = vpath.xpath("@src")[0]
		filename = self.title + "." + bestvpath.rsplit(".", 1)[1]
		if vbase.startswith("rtmp://"):
			return download_rtmp(filename, vbase, bestvpath)
		else:
			return download_urllib(filename, vbase + bestvpath)


def fill_nodes(root_node):
	settings = grab_xml("/playerassets/programs/config/standalone_settings.xml", 24*3600)
	menu_url = settings.xpath("/settings/setting[@name='menuURL']/@value")[0]

	root_menu = grab_xml(menu_url, 3600)
	seen_category_titles = set()
	for menu in root_menu.xpath("//menu"):
		try:
			category_title = menu.xpath("title/text()")[0]
			playlist_url = menu.xpath("playlist/@xmlSrc")[0]
			if category_title in seen_category_titles:
				# append a number to the name
				i = 2
				while True:
					if (category_title+str(i)) not in seen_category_titles:
						category_title += str(i)
						break
					i += 1
			seen_category_titles.add(category_title)
			category_node = Node(category_title, root_node)
			playlist = grab_xml(playlist_url, 3600)
			for video_desc in playlist.xpath("//video"):
				video_desc_url = video_desc.xpath("@src")[0]
				video_title = video_desc.xpath("title/text()")[0].strip()
				SbsNode(video_title, category_node, video_desc_url)
		except IndexError:
			continue
	
