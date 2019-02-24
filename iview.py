from common import grab_json, grab_xml, Node, download_hls
import requests_cache
import urllib.parse

API_URL = "https://iview.abc.net.au/api"
AUTH_URL = "https://iview.abc.net.au/auth"

def format_episode_title(series, ep):
    if ep:
        return series + " " + ep
    else:
        return series

def add_episode(parent, ep_info):
    video_key = ep_info["episodeHouseNumber"]
    series_title = ep_info["seriesTitle"]
    title = ep_info.get("title", None)
    episode_title = format_episode_title(series_title, title)

    IviewEpisodeNode(episode_title, parent, video_key)

class IviewEpisodeNode(Node):
    def __init__(self, title, parent, video_key):
        Node.__init__(self, title, parent)
        self.video_key = video_key
        self.filename = title + ".ts"
        self.can_download = True

    def find_hls_url(self, playlist):
        for video in playlist:
            if video["type"] == "program":
                for quality in ["hls-plus", "hls-high"]:
                    if quality in video:
                        return video[quality].replace("http:", "https:")
        raise Exception("Missing program stream for " + self.video_key)

    def get_auth_details(self):
        with requests_cache.disabled():
            auth_doc = grab_xml(AUTH_URL)
        NS = {
            "auth": "http://www.abc.net.au/iView/Services/iViewHandshaker",
        }
        token = auth_doc.xpath("//auth:tokenhd/text()", namespaces=NS)[0]
        token_url = auth_doc.xpath("//auth:server/text()", namespaces=NS)[0]
        token_hostname = urllib.parse.urlparse(token_url).netloc
        return token, token_hostname

    def add_auth_token_to_url(self, video_url, token, token_hostname):
        parsed_url = urllib.parse.urlparse(video_url)
        hacked_url = parsed_url._replace(netloc=token_hostname, query="hdnea=" + token)
        video_url = urllib.parse.urlunparse(hacked_url)
        return video_url

    def download(self):
        info = grab_json(API_URL + "/programs/" + self.video_key)
        if "playlist" not in info:
            return False
        video_url = self.find_hls_url(info["playlist"])
        token, token_hostname= self.get_auth_details()
        video_url = self.add_auth_token_to_url(video_url, token, token_hostname)
        return download_hls(self.filename, video_url)

class IviewIndexNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.url = url
        self.unique_series = set()

    def fill_children(self):
        info = grab_json(self.url)
        for key in ["carousels", "collections", "index"]:
            for collection_list in info[key]:
                if isinstance(collection_list, dict):
                    for ep_info in collection_list.get("episodes", []):
                        self.add_series(ep_info)

    def add_series(self, ep_info):
        title = ep_info["seriesTitle"]
        if title in self.unique_series:
            return
        self.unique_series.add(title)
        url = API_URL + "/" + ep_info["href"]
        IviewSeriesNode(title, self, url)

class IviewSeriesNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.url = url

    def fill_children(self):
        ep_info = grab_json(self.url)
        series_slug = ep_info["href"].split("/")[1]
        series_url = API_URL + "/series/" + series_slug + "/" + ep_info["seriesHouseNumber"]
        info = grab_json(series_url)
        for ep_info in info.get("episodes", []):
            add_episode(self, ep_info)

class IviewFlatNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.url = url

    def fill_children(self):
        info = grab_json(self.url)
        for ep_info in info:
            add_episode(self, ep_info)


class IviewRootNode(Node):
    def load_categories(self):
        by_category_node = Node("By Category", self)
        def category(name, slug):
            IviewIndexNode(name, by_category_node, API_URL + "/category/" + slug)

        category("Arts & Culture", "arts")
        category("Comedy", "comedy")
        category("Documentary", "docs")
        category("Drama", "drama")
        category("Education", "education")
        category("Lifestyle", "lifestyle")
        category("News & Current Affairs", "news")
        category("Panel & Discussion", "panel")
        category("Regional Australia", "regional")
        category("Sport", "sport")

    def load_channels(self):
        by_channel_node = Node("By Channel", self)
        def channel(name, slug):
            IviewIndexNode(name, by_channel_node, API_URL + "/channel/" + slug)

        channel("ABC1", "abc1")
        channel("ABC2", "abc2")
        channel("ABC3", "abc3")
        channel("ABC4Kids", "abc4kids")
        channel("News", "news")
        channel("ABC Arts", "abcarts")
        channel("iView Exclusives", "iview")

    def load_featured(self):
        IviewFlatNode("Featured", self, API_URL + "/featured")

    def fill_children(self):
        self.load_categories()
        self.load_channels()
        self.load_featured()


def fill_nodes(root_node):
    IviewRootNode("ABC iView", root_node)

