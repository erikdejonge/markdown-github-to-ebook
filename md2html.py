# coding=utf-8
"""
convert markdown to html
"""

import os
import shutil
import uuid
import multiprocessing
from multiprocessing.dummy import Pool
from argparse import ArgumentParser

import subprocess
from subprocess import Popen
from threading import Lock

g_lock = Lock()


def doconversion(f, folder):
    """
    @type f: str, unicode
    @type folder: str, unicode
    @return: None
    """
    global g_lock
    try:
        if "tempfolder" in folder:
            print "searching tempfolder, skipping", folder
            return ""

        tempfolder = "tempfolder" + uuid.uuid4().hex
        cwf = os.path.join(os.getcwd(), folder)
        try:
            g_lock.acquire()

            if os.path.exists(os.path.join(cwf, f.replace(".md", ".html"))):
                print "\033[32m", "file exists skipping" + os.path.join(cwf, f.replace(".md", ".html")), "\033[0m"
                return ""

            ebook = Popen(["ebook", "--f", tempfolder, "--source", "./" + f], stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=cwf)
            ebook.wait()
            so, se = ebook.communicate()
        finally:
            g_lock.release()

        res = str(so) + str(se)

        if len(res.strip()) != 0 or ebook.returncode != 0:
            print 20 * " ", res
        else:
            if os.path.exists(os.path.join(cwf, tempfolder + "/" + f.replace(".md", ".html"))):
                print "\033[33m", "writing:", os.path.join(cwf, f.replace(".md", ".html")), "\033[0m"
                shutil.copyfile(os.path.join(cwf, tempfolder + "/" + f.replace(".md", ".html")), os.path.join(cwf, f.replace(".md", ".html")))

        return ""
    except Exception as e:
        raise

        return str(e)


def startconversion(t):
    """
    @type t: str, unicode
    @return: None
    """
    return doconversion(t[0], t[1])


def convert(folder, ppool, convertlist):
    """
    @type folder: str, unicode
    @type ppool: multiprocessing.Pool
    @return: None
    """
    fl = [x for x in os.listdir(folder)]
    for f in fl:
        if os.path.isdir(os.path.join(folder, f)):
            convert(os.path.join(folder, f), ppool, convertlist)
        else:
            if f.endswith(".md"):
                fp = os.path.join(folder, f)
                c = open(fp).read()
                fp2 = open(fp, "w")
                fp2.write(c.replace(".md", ".html"))
                fp2.close()

                # doconversion(f, folder)
                numitems = len([x for x in os.listdir(folder) if x.endswith(".md")])

                # if numitems > 0:
                #    print "convert:", folder, numitems, "items"
                #ppool.apply_async(doconversion, (f, folder))
                convertlist.append((f, folder))


def toc_files(folder, toc):
    """
    @type folder: str, unicode
    @type toc: str, unicode
    @return: None
    """
    fl = [x for x in os.listdir(folder)]
    for f in fl:
        if os.path.isdir(os.path.join(folder, f)):
            toc = toc_files(os.path.join(folder, f), toc)
        else:
            if f.endswith(".html"):
                dname = os.path.join(folder, f)
                dname = dname.split("/")
                dname = dname[2:]
                dname = "/".join(dname)
                toc += '<a href="' + os.path.join(folder, f).replace("markdown", "").lstrip("/") + '">' + dname.replace("markdown", "").replace(".html", "").replace("_", " ").strip() + '</a><br/>\n'

    return toc


def make_toc(folder, bookname):
    """
    @type folder: str, unicode
    @type bookname: str, unicode
    @return: None
    """
    toc = """
        <html>
           <body>
             <h1>Table of Contents</h1>
             <p style="text-indent:0pt">
     """
    toc = toc_files(folder, toc)
    toc += """
             </p>
           </body>
        </html>"""

    open(folder + "/" + bookname.replace("_", " ") + ".html", "w").write(toc)


def convertmdcode(ext):
    """
    @type ext: str, unicode
    @return: None
    """
    for p in os.popen("find markdown -name  '*.md" + ext + "' -type f").read().split("\n"):
        if os.path.exists(p):
            if ext.lower().strip() == "js":
                extcss = "javascript"
            elif ext.lower().strip() == "h":
                extcss = "c"
            elif ext.lower().strip() == "sh":
                extcss = "bash"
            else:
                extcss = ext

            open(p.replace(".md" + ext, ".md"), "w").write("```" + extcss + "\n" + open(p).read() + "```")
            os.remove(p)


def source_file_rm_or_md(convertcode, targetextension):
    """
    @type convertcode: str, unicode
    @type targetextension: str, unicode
    @return: None
    """
    if targetextension == "rst":
        print "converting rst"

        for p in os.popen("find markdown -name  *.rst -type f").read().split("\n"):
            if len(p.strip()) > 0:
                if os.path.exists(p):
                    print "rst2md:", p, "->", p.lower().replace(".rst", ".md")

                    if not os.path.exists(p.lower().replace(".rst", ".md")):
                        os.system("pandoc -f rst -t markdown_github " + p + " -o " + p.lower().replace(".rst", ".md"))

                    os.remove(p)

        return
    else:
        if convertcode:
            os.system("""find markdown/ -name '*.""" + targetextension + """' -type f -exec bash -c 'mv "$1" "${1/.""" + targetextension + """/.md""" + targetextension + """}"' -- {} \; 2> /dev/null""")
            convertmdcode(targetextension)
        else:
            os.system("cd markdown/*&&sudo find . -name '*." + targetextension + "' -exec rm -rf {} \; 2> /dev/null")


def main():
    """
    main
    """
    parser = ArgumentParser()
    parser.add_argument("-c", "--convertcode", dest="convertcode", help="Convert sourcecode (py, go, coffee and js) to md", action='store_true')
    parser.add_argument("-r", "--restorecode", dest="restorecode", help="Reset the converted code from the markdown archive", action='store_true')
    args, unknown = parser.parse_known_args()
    convertcode = args.convertcode

    if args.restorecode:
        print "\033[32mbusy restoring markdown folder.\033[0m"
        shutil.rmtree("markdown")
        os.system("pigz -d markdown.tar.gz&&tar -xf markdown.tar")

    if not os.path.exists("markdown"):
        print "\033[31m", "no markdown folder", "\033[0m"
        return

    if len(os.listdir("./markdown")) == 0:
        print "\033[31m", "markdown folder is empty", "\033[0m"
        return

    os.system("rm -f markdown.tar.gz; tar -cf markdown.tar ./markdown; pigz markdown.tar;")
    booktitle = "".join(os.listdir("markdown"))
    specialchar = False
    scs = [" ", "&", "?"]

    for c in scs:
        if c in booktitle.strip():
            specialchard = {1: c,
                            2: booktitle}

            print "\033[31m", "directory with special char", specialchard, "\033[0m"
            specialchar = True
            break

    if specialchar is True:
        return

    print "\033[32m" + booktitle, "\033[0m"
    print "\033[33m" + "converting", "\033[0m"
    source_file_rm_or_md(convertcode, "sh")
    source_file_rm_or_md(convertcode, "rst")
    source_file_rm_or_md(convertcode, "h")
    source_file_rm_or_md(convertcode, "py")
    source_file_rm_or_md(convertcode, "go")
    source_file_rm_or_md(convertcode, "js")
    source_file_rm_or_md(convertcode, "coffee")
    source_file_rm_or_md(convertcode, "c")
    print "\033[33m" + "cleaning", "\033[0m"
    os.system("sudo find ./markdown/* -name '.git' -exec rm -rf {} \; 2> /dev/null")
    os.system("cd markdown/*&&sudo find . -type l -exec rm -f {} \; 2> /dev/null")
    os.system("cd markdown/*&&sudo find . -name 'man' -exec rm -rf {} \; 2> /dev/null")
    os.system("cd markdown/*&&sudo find . -name 'commands' -exec rm -rf {} \; 2> /dev/null")
    os.system("cd markdown/*&&sudo find . -name 'Godeps*' -exec rm -rf {} \; 2> /dev/null")
    os.system("cd markdown/*&&sudo find . -name '_Godeps*' -exec rm -rf {} \; 2> /dev/null")
    os.system("sudo find markdown -depth -empty -delete")
    os.system("""find markdown/ -name '*.txt' -type f -exec bash -c 'mv "$1" "${1/.txt/.md}"' -- {} \; 2> /dev/null""")
    os.system("""find markdown/ -name '*.rst' -type f -exec bash -c 'mv "$1" "${1/.rst/.md}"' -- {} \; 2> /dev/null""")
    os.system("cd markdown/*&&sudo find . -name 'tempfolder*' -exec rm -rf {} \; 2> /dev/null")
    print "\033[33m", "pandoc", "\033[0m"
    ppool = Pool(multiprocessing.cpu_count())
    convertlist = []
    convert("markdown", ppool, convertlist)

    # for i in convertlist:
    #    res = startconversion(i)
    for res in ppool.map(startconversion, convertlist):
        if len(res.strip()) > 0:
            print "\033[31m", res, "\033[0m"

    ppool.close()
    ppool.join()
    os.system("cd markdown/*&&sudo find . -name 'tempfolder*' -exec rm -rf {} \; 2> /dev/null")
    make_toc("markdown", booktitle)


if __name__ == "__main__":
    main()
