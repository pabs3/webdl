import sys

# Python 2.7 compatibility
try:
    import cookielib
    import urllib
    import urllib2
    import urlparse

    class dummy_http_module:
        cookiejar = cookielib
    sys.modules['http'] = dummy_http_module
    sys.modules['http.cookiejar'] = dummy_http_module.cookiejar

    class dummy_urllib_module:
        parse = urlparse
        request = urllib2
    sys.modules['urllib'] = dummy_urllib_module
    sys.modules['urllib.parse'] = dummy_urllib_module.parse
    sys.modules['urllib.request'] = dummy_urllib_module.request
    dummy_urllib_module.parse.urlencode = urllib.urlencode

except ImportError:
    pass

