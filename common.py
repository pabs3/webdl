from lxml import etree, html
import cookielib
import json
try:
    import hashlib
except ImportError:
    import md5 as hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib
import urllib2
import urlparse


try:
    import autosocks
    autosocks.try_autosocks()
except ImportError:
    pass

CACHE_DIR = os.path.expanduser("~/.cache/webdl")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:21.0) Gecko/20100101 Firefox/21.0"

class Node(object):
    def __init__(self, title, parent=None):
        self.title = title
        if parent:
            parent.children.append(self)
        self.parent = parent
        self.children = []
        self.can_download = False

    def get_children(self):
        if not self.children:
            self.fill_children()
        return self.children

    def fill_children(self):
        pass

    def download(self):
        raise NotImplemented


def load_root_node():
    root_node = Node("Root")

    import iview
    iview.fill_nodes(root_node)

    import sbs
    sbs.fill_nodes(root_node)

    import plus7
    plus7.fill_nodes(root_node)

    import brightcove
    brightcove.fill_nodes(root_node)

    return root_node

valid_chars = frozenset("-_.()!@#%^ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
def sanify_filename(filename):
    filename = filename.encode("ascii", "ignore")
    filename = "".join(c for c in filename if c in valid_chars)
    return filename

cookiejar = cookielib.CookieJar()
urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
def _urlopen(url, referrer=None):
    req = urllib2.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    if referrer:
        req.add_header("Referer", referrer)
    return urlopener.open(req)

def urlopen(url, max_age):
### print url
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    if max_age <= 0:
        return _urlopen(url)

    filename = hashlib.md5(url).hexdigest()
    filename = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filename):
        file_age = int(time.time()) - os.path.getmtime(filename)
        if file_age < max_age:
            return open(filename)

    src = _urlopen(url)
    dst = open(filename, "w")
    try:
        shutil.copyfileobj(src, dst)
    except Exception, e:
        try:
            os.unlink(filename)
        except OSError:
            pass
        raise e
    src.close()
    dst.close()

    return open(filename)

def grab_text(url, max_age):
    f = urlopen(url, max_age)
    text = f.read().decode("utf-8")
    f.close()
    return text

def grab_html(url, max_age):
    f = urlopen(url, max_age)
    doc = html.parse(f, html.HTMLParser(encoding="utf-8", recover=True))
    f.close()
    return doc

def grab_xml(url, max_age):
    f = urlopen(url, max_age)
    doc = etree.parse(f, etree.XMLParser(encoding="utf-8", recover=True))
    f.close()
    return doc

def grab_json(url, max_age, skip_assignment=False, skip_function=False):
    f = urlopen(url, max_age)
    if skip_assignment:
        text = f.read()
        pos = text.find("=")
        doc = json.loads(text[pos+1:])
    elif skip_function:
        text = f.read()
        pos = text.find("(")
        rpos = text.rfind(")")
        doc = json.loads(text[pos+1:rpos])
    else:
        doc = json.load(f)
    f.close()
    return doc

def exec_subprocess(cmd):
    try:
        p = subprocess.Popen(cmd)
        ret = p.wait()
        if ret != 0:
            print >>sys.stderr, cmd[0], "exited with error code:", ret
            return False
        else:
            return True
    except OSError, e:
        print >>sys.stderr, "Failed to run", cmd[0], e
    except KeyboardInterrupt:
        print "Cancelled", cmd
        try:
            p.terminate()
            p.wait()
        except KeyboardInterrupt:
            p.send_signal(signal.SIGKILL)
            p.wait()
    return False


def convert_flv_mp4(orig_filename):
    basename = os.path.splitext(orig_filename)[0]
    flv_filename = basename + ".flv"
    mp4_filename = basename + ".mp4"
    if orig_filename != flv_filename:
        os.rename(orig_filename, flv_filename)
    print "Converting %s to mp4" % flv_filename
    if not avconv_remux(flv_filename, mp4_filename):
        # failed, error has already been logged
        return
    try:
        flv_size = os.stat(flv_filename).st_size
        mp4_size = os.stat(mp4_filename).st_size
        if abs(flv_size - mp4_size) < 0.05 * flv_size:
            os.unlink(flv_filename)
        else:
            print >>sys.stderr, "The size of", mp4_filename, "is suspicious, did avconv fail?"
    except Exception, e:
        print "Conversion failed", e

def avconv_remux(infile, outfile):
    cmd = [
        "avconv",
        "-i", infile,
        "-acodec", "copy",
        "-vcodec", "copy",
        outfile,
    ]
    return exec_subprocess(cmd)

def convert_filename(filename):
    if os.path.splitext(filename.lower())[1] in (".mp4", ".flv"):
        f = open(filename)
        fourcc = f.read(4)
        f.close()
        if fourcc == "FLV\x01":
            convert_flv_mp4(filename)

def download_rtmp(filename, vbase, vpath, hash_url=None):
    filename = sanify_filename(filename)
    print "Downloading: %s" % filename
    if vpath.endswith(".flv"):
        vpath = vpath[:-4]
    cmd = [
        "rtmpdump",
        "-o", filename,
        "-r", vbase,
        "-y", vpath,
    ]
    if hash_url is not None:
        cmd += ["--swfVfy", hash_url]
    if exec_subprocess(cmd):
        convert_filename(filename)
        return True
    else:
        return False

def download_urllib(filename, url, referrer=None):
    filename = sanify_filename(filename)
    print "Downloading: %s" % filename
    try:
        src = _urlopen(url, referrer)
        dst = open(filename, "w")
        while True:
            buf = src.read(1024*1024)
            if not buf:
                break
            dst.write(buf)
            sys.stdout.write(".")
            sys.stdout.flush()
        print
    except KeyboardInterrupt:
        print "\nCancelled", url
        return False
    finally:
        try:
            src.close()
        except:
            pass
        try:
            dst.close()
        except:
            pass

    convert_filename(filename)
    return True

def download_hls_get_stream(url, hack_url_func):
    url = hack_url_func(url)

    def parse_bandwidth(line):
        params = line.split(":", 1)[1].split(",")
        for kv in params:
            k, v = kv.split("=", 1)
            if k == "BANDWIDTH":
                return int(v)
        return 0

    m3u8 = grab_text(url, 0)
    best_bandwidth = None
    best_url = None
    for line in m3u8.split("\n"):
        if line.startswith("#EXT-X-STREAM-INF:"):
            bandwidth = parse_bandwidth(line)
            if best_bandwidth is None or bandwidth > best_bandwidth:
                best_bandwidth = bandwidth
                best_url = None
        elif not line.startswith("#"):
            if best_url is None:
                best_url = line.strip()

    if not best_url:
        raise Exception("Failed to find best stream for HLS: " + url)

    return best_url

def download_hls_segments(tmpdir, url, hack_url_func):
    m3u8 = grab_text(url, 0)
    result = []

    local_m3u8_filename = tmpdir + "/index.m3u8"
    local_m3u8 = open(local_m3u8_filename, "w")

    i = 1
    fail_if_not_last_segment = None
    for line in m3u8.split("\n"):
        if not line.strip():
            continue
        if line.startswith("#"):
            local_m3u8.write(line + "\n")
            continue

        if fail_if_not_last_segment:
            raise e

        outfile = "%s/segment_%d.ts" % (tmpdir, i)
        i += 1
        try:
            download_hls_fetch_segment(hack_url_func(line), outfile)
        except urllib2.HTTPError, e:
            fail_if_not_last_segment = e
            continue
        local_m3u8.write(outfile + "\n")
        sys.stdout.write(".")
        sys.stdout.flush()

    sys.stdout.write("\n")

    local_m3u8.close()
    return local_m3u8_filename

def download_hls_fetch_segment(segment, outfile):
    try:
        src = _urlopen(segment)
        dst = open(outfile, "w")
        shutil.copyfileobj(src, dst)
    except:
        print >>sys.stderr, "Failed to fetch", segment
        raise
    finally:
        try:
            src.close()
        except:
            pass
        try:
            dst.close()
        except:
            pass

def download_hls(filename, m3u8_master_url, hack_url_func=None):
    if hack_url_func is None:
        hack_url_func = lambda url: url

    tmpdir = tempfile.mkdtemp(prefix="webdl-hls")
    filename = sanify_filename(filename)

    print "Downloading: %s" % filename

    try:
        best_stream_url = download_hls_get_stream(m3u8_master_url, hack_url_func)
        local_m3u8 = download_hls_segments(tmpdir, best_stream_url, hack_url_func)
        avconv_remux(local_m3u8, filename)
        return True
    except KeyboardInterrupt:
        print "\nCancelled", m3u8_master_url
        return False
    finally:
        shutil.rmtree(tmpdir)

def natural_sort(l, key=None):
    ignore_list = ["a", "the"]
    def key_func(k):
        if key is not None:
            k = key(k)
        k = k.lower()
        newk = []
        for c in re.split("([0-9]+)", k):
            c = c.strip()
            if c.isdigit():
                newk.append(int(c))
            else:
                for subc in c.split():
                    if subc not in ignore_list:
                        newk.append(subc)
        return newk

    return sorted(l, key=key_func)

def append_to_qs(url, params):
    r = list(urlparse.urlsplit(url))
    qs = urlparse.parse_qs(r[3])
    for k, v in params.iteritems():
        if v is not None:
            qs[k] = v
        elif qs.has_key(k):
            del qs[k]
    r[3] = urllib.urlencode(qs, True)
    url = urlparse.urlunsplit(r)
    return url

