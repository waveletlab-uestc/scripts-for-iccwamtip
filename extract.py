#!/usr/bin/env python3

__doc__ = """
从 CMT 下载的压缩文件（支持 Submission、Feedback 和 Camera Ready 文件）提取论文或者其他文件
"""

__author__ = 'HeXi'

import os
import sys
import shutil
import zipfile
from random import randint

payment_keys = ['payment', '付款', '缴费', '支付', 'fee', 'receipt', '转账']
paper_keys = ['paper', '论文', 'manuscript', 'camera', 'essay']
report_keys = ['report', 'plagiarism', 'plagrism', '查重']
copyright_keys = ['copyright']
other_keys = []

def is_payment(fname):
    base_name = os.path.splitext(fname)[0].lower()
    ext = os.path.splitext(fname)[-1].lower()
    exclude_keys = paper_keys + report_keys + copyright_keys + other_keys
    if ext in ['.png', '.jpg', '.jpeg']:
        return True
    for key in exclude_keys:
        if key in base_name:
            return False
    for key in payment_keys:
        if key in base_name:
            return True
    return False

def is_camera(fname):
    return is_paper(fname, valid_exts=['.docx'], invalid_exts=['.pdf', '.png', '.jpg', '.jpeg'])

def is_paper(fname, valid_exts=['.docx', '.doc', '.pdf'], invalid_exts=['.png', '.jpeg', 'jpg']):
    base_name = os.path.splitext(fname)[0].lower()
    ext = os.path.splitext(fname)[-1].lower()
    # plagrism is the wrong spelling of plagiarism
    exclude_keys = other_keys + payment_keys + report_keys
    for key in exclude_keys:
        if key in base_name:
            return False
    for key in paper_keys:
        if key in base_name and ext not in invalid_exts:
            return True
    if ext in valid_exts:
        return True
    return False


def is_copyright(fname):
    base_name = os.path.splitext(fname)[0].lower()
    ext = os.path.splitext(fname)[-1].lower()
    for key in copyright_keys:
        if key in base_name:
            return True


def unzip(path, folderPath):
    """
    解压文件
    :param path:       压缩文件路径
    :param folderPath: 解压后文件路径
    """

    zfile = zipfile.ZipFile(path)
    files = zfile.namelist()
    for f in files:
        zfile.extract(f, folderPath)


def filter_files(src, dst, reserve=is_paper, unique=True):
    """
    将符合 reserve 条件的文件移动到 dst 目录下，通常情况下一个 id 内只有一个文件
    除非 unique 为 False
    <id>/[Submission]/<files>
    :param src: 所有文件根目录
    :param dst: 文件移动后的新目录
    """

    ids = set()

    for dirpath, dnames, fnames in os.walk(src):
        for fname in fnames:
            path = os.path.join(dirpath, fname.replace('\\', os.path.sep))
            id_ = path.split(os.path.sep)[1]
            true_name = path.split(os.path.sep)[-1]
            ext = os.path.splitext(true_name)[-1].lower()
            if reserve(true_name):
                if id_ in ids and unique:
                    continue
                if id_ in ids:
                    for i in range(1, 11):
                        new_id = "{}-{}".format(id_, i)
                        if new_id not in ids:
                            id_ = new_id
                            break
                ids.add(id_)
                # 移动文件
                src2 = os.path.join(dirpath, fname)
                dst2 = os.path.join(dst, id_ + ext)
                shutil.move(src2, dst2)
                print("{}\t<-- {}".format(dst2, src2))


def compress_files(src, dstzip):
    """
    压缩 src 文件夹下内的所有文件为名为 dstzip 的 zip 压缩文件
    :param src: 源地址
    "param dstzip: 压缩后的目标文件
    """

    with zipfile.ZipFile(dstzip, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dnames, fnames in os.walk(src):
            out_path = dirpath.lstrip(src).replace(os.path.sep, '/')
            if out_path:
                out_path = out_path + '/'
            for filename in fnames:
                z.write(os.path.join(dirpath, filename), out_path + filename)


def make_random_dir():
    dir_ = "{}.dir".format(randint(10000, 99999))
    os.mkdir(dir_)
    return dir_


def usage():
    print("extract.py [paper|payment] {sources.zip} {destination.zip}")
    print("e.g. extract.py paper Submission.zip papers.zip")


def main():
    """
    先从 sourcePath 路径解压文件到 extractDir
    然后从 extractDir 提取最终文件并改名 放到 dstDir 中
    再压缩 dstDir 文件夹中文件到 toFile
    最后删除所有中间文件
    """

    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
    elif len(sys.argv) == 3:
        mode = 'paper'
        source_zip = sys.argv[1]
        distance_zip = sys.argv[2]
    else:
        mode = sys.argv[1]
        source_zip = sys.argv[2]
        distance_zip = sys.argv[3]

    extract_dir = make_random_dir()
    unzip(source_zip, extract_dir)

    distance_dir = make_random_dir()
    if 'paper' == mode:
        filter_files(extract_dir, distance_dir, reserve=is_paper)
    elif 'copyright' == mode:
        filter_files(extract_dir, distance_dir, reserve=is_copyright)
    elif 'camera' == mode:
        filter_files(extract_dir, distance_dir, reserve=is_camera)
    elif 'payment' == mode:
        filter_files(extract_dir, distance_dir, reserve=is_payment, unique=False)
    else:
        print("Invalid mode")
        usage()

    compress_files(distance_dir, distance_zip)

    shutil.rmtree(extract_dir)
    shutil.rmtree(distance_dir)


if __name__ == '__main__':
    main()
