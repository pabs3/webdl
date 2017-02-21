#!/usr/bin/env python3

from common import load_root_node, natural_sort


def choose(options, allow_multi):
    reverse_map = {}
    for i, (key, value) in enumerate(options):
        print("%3d) %s" % (i+1, key))
        reverse_map[i+1] = value
    print("  0) Back")
    while True:
        try:
            values = list(map(int, input("Choose> ").split()))
            if len(values) == 0:
                continue
            if 0 in values:
                return
            values = [reverse_map[value] for value in values if value in reverse_map]
            if allow_multi:
                return values
            else:
                if len(values) == 1:
                    return values[0]
        except (ValueError, IndexError):
            print("Invalid input, please try again")
            pass

def main():
    node = load_root_node()

    while True:
        options = []
        will_download = True
        for n in node.get_children():
            options.append((n.title, n))
            if not n.can_download:
                will_download = False
        options = natural_sort(options, key=lambda x: x[0])
        result = choose(options, allow_multi=will_download)
        if result is None:
            if node.parent is not None:
                node = node.parent
            else:
                break
        elif will_download:
            for n in result:
                if not n.download():
                    input("Press return to continue...\n")
        else:
            node = result

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")

