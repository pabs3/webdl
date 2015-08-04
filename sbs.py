#!/usr/bin/env python

from common import grab_html, grab_json, grab_xml, download_hls, Node

import json

BASE = "http://www.sbs.com.au"
FULL_VIDEO_LIST = BASE + "/api/video_feed/f/Bgtm9B/sbs-section-programs/?form=json"
VIDEO_URL = BASE + "/ondemand/video/single/%s"

NS = {
    "smil": "http://www.w3.org/2005/SMIL21/Language",
}


class SbsVideoNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.video_id = url.split("/")[-1]
        self.can_download = True

    def download(self):
        doc = grab_html(VIDEO_URL % self.video_id, 0)
        player_params = self.get_player_params(doc)
        release_url = player_params["releaseUrls"]["html"]

        doc = grab_xml(release_url, 0)
        video = doc.xpath("//smil:video", namespaces=NS)[0]
        video_url = video.attrib["src"]
        if not video_url:
            raise Exception("Unsupported video %s: %s" % (self.video_id, self.title))
        filename = self.title + ".mp4"
        return download_hls(filename, video_url)

    def get_player_params(self, doc):
        for script in doc.xpath("//script"):
            if not script.text:
                continue
            for line in script.text.split("\n"):
                s = "var playerParams = {"
                if s in line:
                    p1 = line.find(s) + len(s) - 1
                    p2 = line.find("};", p1) + 1
                    if p1 >= 0 and p2 > 0:
                        return json.loads(line[p1:p2])
        raise Exception("Unable to find player params for %s: %s" % (self.video_id, self.title))


class SbsNavNode(Node):
    def create_video_node(self, entry_data):
        SbsVideoNode(entry_data["title"], self, entry_data["id"])

    def find_existing_child(self, path):
        for child in self.children:
            if child.title == path:
                return child

class SbsRootNode(SbsNavNode):
    def __init__(self, parent):
        Node.__init__(self, "SBS", parent)

    def fill_children(self):
        full_video_list = grab_json(FULL_VIDEO_LIST, 3600)
        category_and_entry_data = self.explode_videos_to_unique_categories(full_video_list)
        for category_path, entry_data in category_and_entry_data:
            nav_node = self.create_nav_node(self, category_path)
            nav_node.create_video_node(entry_data)

    def explode_videos_to_unique_categories(self, full_video_list):
        for entry_data in full_video_list["entries"]:
            for category_data in entry_data["media$categories"]:
                category_path = self.calculate_category_path(
                    category_data["media$scheme"],
                    category_data["media$name"],
                )
                if category_path:
                    yield category_path, entry_data

    def calculate_category_path(self, scheme, name):
        if not scheme:
            return
        if scheme == name:
            return
        name = name.split("/")
        if name[0] != scheme:
            name.insert(0, scheme)
        return name

    def create_nav_node(self, parent, category_path):
        if not category_path:
            return parent

        current_path = category_path[0]
        current_node = parent.find_existing_child(current_path)
        if not current_node:
            current_node = SbsNavNode(current_path, parent)
        return self.create_nav_node(current_node, category_path[1:])

def fill_nodes(root_node):
    SbsRootNode(root_node)
