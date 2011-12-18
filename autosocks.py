# vim:ts=4:sts=4:sw=4:noet

import subprocess


def detect_gnome():
	""" Gnome via python-gconf """
	from gconf import client_get_default
	gconf_client = client_get_default()
	mode = gconf_client.get_string("/system/proxy/mode")
	if mode != "manual":
		return None, None
	host = gconf_client.get_string("/system/proxy/socks_host")
	port = gconf_client.get_int("/system/proxy/socks_port")
	return host, port

def detect_osx():
	""" OS X 10.5 and up via PyObjC """
	from SystemConfiguration import SCDynamicStoreCopyProxies
	osx_proxy = SCDynamicStoreCopyProxies(None)
	if osx_proxy.get("SOCKSEnable"):
		host = osx_proxy.get("SOCKSProxy")
		port = int(osx_proxy.get("SOCKSPort"))
		return host, port
	return None, None

def detect_kde():
	""" KDE via command line, why no python bindings for KDE proxy settings? """
	if os.environ.get("KDE_FULL_SESSION") != "true":
		return None, None
	p = subprocess.Popen(
		[
			"kreadconfig",
			"--file",
			"kioslaverc",
			"--group",
			"Proxy Settings",
			"--key",
			"socksProxy",
		],
		shell=True,
		stdout=subprocess.PIPE,
	)
	host, port = p.stdout.readline()[:-1].split(":")
	p.close()
	port = int(port)
	return host, port

def detect_env():
	""" fallback to environment variables """
	socks_environ = os.environ.get("SOCKS_SERVER")
	if not socks_environ:
		return None, None
	host, port = socks_environ
	port = int(port)
	return host, port


def configure_socks(host, port):
	""" hijack socket.socket using SocksiPy """
	try:
		import socks, socket
	except ImportError:
		print >>sys.stderr, "Failed to use configured SOCKS proxy:", host, port
		print >>sys.stderr, "Try installing SocksiPy: http://socksipy.sf.net"
		return False

	socket.socket = socks.socksocket
	socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, host, port)
	return True


def try_autosocks():
	functions = [
		detect_gnome,
		detect_osx,
		detect_kde,
		detect_env,
	]
	for func in functions:
		host, port = None, None
		try:
			host, port = func()
		except Exception, e:
			pass
		if host is not None and port is not None:
			return configure_socks(host, port)
	return False

