from common import grab_json, grab_xml, Node, download_hls
import urlparse

API_URL = "http://iview.abc.net.au/api"
AUTH_URL = "http://iview.abc.net.au/auth"

def format_episode_title(series, ep):
    if ep:
        return series + " " + ep
    else:
        return series

class IviewEpisodeNode(Node):
    def __init__(self, title, parent, video_key):
        Node.__init__(self, title, parent)
        self.video_key = video_key
        self.filename = title + ".ts"
        self.can_download = True

    def find_hls_url(self, playlist):
        for video in playlist:
            if video["type"] == "program":
                return video["hls-high"]
        raise Exception("Missing hls-high program stream for " + self.video_key)

    def get_auth_details(self):
        auth_doc = grab_xml(AUTH_URL, 0)
        NS = {
            "auth": "http://www.abc.net.au/iView/Services/iViewHandshaker",
        }
        token = auth_doc.xpath("//auth:tokenhd/text()", namespaces=NS)[0]
        token_url = auth_doc.xpath("//auth:server/text()", namespaces=NS)[0]
        token_hostname = urlparse.urlparse(token_url).netloc
        return token, token_hostname

    def hack_url_auth_token(self, video_url, token, token_hostname):
        parsed_url = urlparse.urlparse(video_url)
        hacked_url = parsed_url._replace(netloc=token_hostname, query="hdnea=" + token)
        video_url = urlparse.urlunparse(hacked_url)
        return video_url

    def download(self):
        info = grab_json(API_URL + "/programs/" + self.video_key, 3600)
        video_url = self.find_hls_url(info["playlist"])
        token, token_hostname= self.get_auth_details()
        hack_url = lambda url: self.hack_url_auth_token(url, token, token_hostname)
        return download_hls(self.filename, video_url, hack_url)


class IviewIndexNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.url = url
        self.series_map = {}

    def add_episode(self, ep_info):
        video_key = ep_info["episodeHouseNumber"]
        series_title = ep_info["seriesTitle"]
        title = ep_info.get("title", None)
        episode_title = format_episode_title(series_title, title)

        series_node = self.series_map.get(series_title, None)
        if not series_node:
            series_node = Node(series_title, self)
            self.series_map[series_title] = series_node

        IviewEpisodeNode(episode_title, series_node, video_key)

    def fill_children(self):
        info = grab_json(self.url, 3600)
        for index_list in info["index"]:
            for ep_info in index_list["episodes"]:
                self.add_episode(ep_info)

class IviewFlatNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.url = url

    def add_episode(self, ep_info):
        video_key = ep_info["episodeHouseNumber"]
        series_title = ep_info["seriesTitle"]
        title = ep_info.get("title", None)
        episode_title = format_episode_title(series_title, title)

        IviewEpisodeNode(episode_title, self, video_key)

    def fill_children(self):
        info = grab_json(self.url, 3600)
        for ep_info in info:
            self.add_episode(ep_info)


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
        category("Sport", "sport")

    def load_channels(self):
        by_channel_node = Node("By Channel", self)
        def channel(name, slug):
            IviewIndexNode(name, by_channel_node, API_URL + "/channel/" + slug)

        channel("ABC1", "abc1")
        channel("ABC2", "abc2")
        channel("ABC3", "abc3")
        channel("ABC4Kids", "abc4kids")
        channel("iView Exclusives", "iview")

    def load_featured(self):
        IviewFlatNode("Featured", self, API_URL + "/featured")

    def fill_children(self):
        self.load_categories()
        self.load_channels()
        self.load_featured()


def fill_nodes(root_node):
    IviewRootNode("ABC iView", root_node)

