
import os.path
import argparse
from unicodecsv import DictReader, DictWriter


def main():
    prs = argparse.ArgumentParser()

    prs.add_argument('--count', type=int, default=100)

    prs.add_argument('file', type=file)

    args = prs.parse_args()

    count = args.count
    assert count > 0
    path = os.path.abspath(args.file.name)
    root, ext = os.path.splitext(path)
    new_path = '%s_trimmed_%s%s' % (root, count, ext)

    reader = DictReader(open(path))
    new_entries = []
    for i in range(count):
        new_entries.append(next(reader))

    with open(new_path, 'w') as new_file:
        writer = DictWriter(new_file, reader.unicode_fieldnames)
        writer.writerows(new_entries)

    print open(new_path).read()


if __name__ == '__main__':
    main()
