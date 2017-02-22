import requests_cache
from common import grab_html, grab_json, grab_xml, download_hls, Node, append_to_qs

import json

BASE = "http://www.sbs.com.au"
FULL_VIDEO_LIST = BASE + "/api/video_search/v2/?m=1&filters={section}{Programs}"
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
        with requests_cache.disabled():
            doc = grab_html(VIDEO_URL % self.video_id)
        player_params = self.get_player_params(doc)
        release_url = player_params["releaseUrls"]["html"]

        with requests_cache.disabled():
            doc = grab_xml(release_url if not release_url.startswith("//") else "https:" + release_url)
        video = doc.xpath("//smil:video", namespaces=NS)[0]
        video_url = video.attrib["src"]
        if not video_url:
            raise Exception("Unsupported video %s: %s" % (self.video_id, self.title))
        filename = self.title + ".ts"
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
        all_video_entries = self.load_all_video_entries()
        category_and_entry_data = self.explode_videos_to_unique_categories(all_video_entries)
        for category_path, entry_data in category_and_entry_data:
            nav_node = self.create_nav_node(self, category_path)
            nav_node.create_video_node(entry_data)

    def load_all_video_entries(self):
        offset = 1
        amount = 500
        while True:
            url = append_to_qs(FULL_VIDEO_LIST, {"range": "%s-%s" % (offset, offset+amount)})
            data = grab_json(url)
            entries = data["entries"]
            if len(entries) == 0:
                break
            for entry in entries:
                yield entry
            offset += amount

    def explode_videos_to_unique_categories(self, all_video_entries):
        for entry_data in all_video_entries:
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
