#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import load_root_node
import sys

def choose(options, allow_multi):
	skeys = sorted(options.keys())
	for i, key in enumerate(skeys):
		print " %d) %s" % (i+1, key)
	print " 0) Back"
	while True:
		try:
			values = map(int, raw_input("Choose> ").split())
			if len(values) == 0:
				continue
			if 0 in values:
				return
			values = [options[skeys[value-1]] for value in values]
			if allow_multi:
				return values
			else:
				if len(values) == 1:
					return values[0]
		except ValueError, IndexError:
			print >>sys.stderr, "Invalid input, please try again"
			pass

def main():
	node = load_root_node()

	while True:
		options = {}
		will_download = True
		for n in node.children:
			options[n.title] = n
			if not n.can_download:
				will_download = False
		result = choose(options, allow_multi=will_download)
		if result is None:
			if node.parent is not None:
				node = node.parent
			else:
				break
		elif will_download:
			for n in result:
				if not n.download():
					raw_input("Press return to continue...\n")
		else:
			node = result

if __name__ == "__main__":
	try:
		main()
	except (KeyboardInterrupt, EOFError):
		print "\nExiting..."

