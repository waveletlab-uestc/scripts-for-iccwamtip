#!/usr/bin/env python3

import os
import re
import shutil
import zipfile
from collections import OrderedDict

from docx import Document


tracks = OrderedDict({
    'Theory and Experiment': 'theory-and-experiment.txt',
    'Multimedia Technology': 'multimedia-technology.txt',
    'Embedded System and Others': 'embedded-system-and-others.txt',
})


def read_file_list(fname):
    with open(fname) as fp:
        return [id.strip()+'.docx' for id in fp.readlines() if id.strip() != '']


def get_pages(doc):
    """获取 docx 文档的页数"""
    with zipfile.ZipFile(doc) as zf:
        appxml = zf.read('docProps/app.xml').decode()
        return int(re.search('(?<=<Pages>)\s*\d+\s*(?=</Pages>)', appxml).group(0))


def main():
    dir = '../papers'
    #shutil.rmtree(dir, ignore_errors=True)
    if not os.path.exists(dir):
        os.mkdir(dir)
    start = 1
    for track_id, fname in enumerate(tracks.values(), 1):
        for no, name in enumerate(read_file_list(fname), 1):
            new_name = os.path.join(dir, f"#{track_id:02}_{no:02}.{start}.docx")
            shutil.copyfile(new_name, name)
            #shutil.copyfile(name, new_name)
            start += get_pages(name)



if __name__ == '__main__':
    main()

