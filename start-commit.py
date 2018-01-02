"""
commit failure cases
 * mixing unit test commits with non-unittest commits
 * mixing unit test commits from different projects
 * mixing xcb and other binaries with code
 * check is sln is being committed most likely this is undesired
 * wc has unversioned *.h or *.cpp files (mostlikely forgotten?)
 * ...
"""
import sys
import os
import argparse
import re
import subprocess
import xml.etree.ElementTree as ET
import six.moves.urllib as urllib

# parse cli arguments supplied by tortoise SVN
# https://tortoisesvn.net/docs/release/TortoiseSVN_en/tsvn-dug-settings.html#tsvn-dug-settings-hooks
parser = argparse.ArgumentParser(description='svn manual_precommit_hook.')
parser.add_argument('path', type=str)
parser.add_argument('messageFile', type=str)
parser.add_argument('cwd', type=str)
parser.add_argument('-d', "--debug",
                    help="enable debug output",
                    action="store_true")
args = parser.parse_args()


def runCommand(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as e:
        print("cmd: "+" ".join(e.cmd))
        print("failed with exit code: " + str(e.returncode))
        print("stdout:\n" + e.output.decode())
        raise e


def Assert(expected, actual):
    if(expected != actual):
        raise Exception("Assertion failure\n  Expected: "
                        + str(expected)
                        + "\n  Actual: "
                        + str(actual))


def AssertFail():
    raise Exception("Assertion failure: forced error")


def ObtainChangesetLog(path, changeset):
    revXML = runCommand([
        'svn', 'log', path, '--xml', '-c', str(changeset)
        ])
    return ET.fromstring(revXML)


def GetRelativeURL(path):
    infoXml = runCommand([
        'svn', 'info', '--xml', path])
    root = ET.fromstring(infoXml)
    e = root.findall("./entry/relative-url")
    Assert(1, len(e))
    return urllib.parse.unquote(e[0].text)


def GetWCMergeInfo():
    propertiesDiff = runCommand([
        'svn', 'diff', '--properties-only', '-N', './'
    ])
    regex = re.compile('^[\s]*Merged [^:]*:.*$', re.MULTILINE)
    mergeInfoList = regex.findall(propertiesDiff)
    if len(mergeInfoList) == 0:
        return None

    mergeSets = {}
    for mergeinfo in mergeInfoList:
        # split mergeinfo in path and rev
        # "  Merged  /f1/f2/f3:r102-200,202
        (path, changeset) = mergeinfo.split(":")

        # extract merge path
        # i.e. path starts from first '/'
        # add the root repo placeholder '^'
        path = "^" + path[path.find("/"):]

        # extact merged change-sets
        # i.e. remove the 'r' prefix
        changeset = changeset[1:].strip()

        if(args.debug):
            print("merge-path: " + path)
            print("merge_changes: " + changeset)
        mergeSets[path] = changeset

    return mergeSets


def exception_handler(exception_type, exception, traceback):
    # All your trace are belong to us!
    # your format
    print(str(exception_type.__name__) + " : " + str(exception))


def countRevisions(logData):
    return len(logData.findall("./logentry"))


class RevisionRangeParser:
    """parse an svn revision Range
    e.g. 'r102-200,202'
    """

    @staticmethod
    def parse(revStr):
        """
        e.g. 'r102-200,202'
        """
        assert(revStr[0] == 'r')
        revStr = revStr[1:]
        ranges = revStr.split(',')
        revs = []
        for r in ranges:
            revs += RevisionRangeParser._parseRange(r)
        return revs
    
    @staticmethod
    def _parseRange(revRangeStr):
        """
        e.g. '102-200', '202'
        """
        assert(revRangeStr.find(',') == -1)
        rangeSepIdx = revRangeStr.find('-')
        if (rangeSepIdx == -1):
            return [int(revRangeStr)]
        else:
            start = int(revRangeStr[0:rangeSepIdx])
            stop = int(revRangeStr[rangeSepIdx+1:])
            return list(range(start, stop+1))


def GetYoungestMergeSet(mergeSets):
    youngestPath = None
    youngestRev = -1
    for (path, revStr) in mergeSets.items():
        revs = RevisionRangeParser.parse("r"+revStr)
        maxRev = max(revs)
        if (maxRev > youngestRev):
            youngestPath = path
            youngestRev = max(revs)
        elif (maxRev == youngestRev):
            assert(False)
    youngestmergeSet = (youngestPath, mergeSets[youngestPath])
    if args.debug:
        print("mergesource: " + str(youngestmergeSet))
    return youngestmergeSet


# ============================================================
# don't show error trace in non-debug mode
if(args.debug is False):
    sys.excepthook = exception_handler


if not os.path.isdir(args.cwd) or os.stat(os.getcwd()) != os.stat(args.cwd):
    raise Exception("args.cwd and actual cwd are different")

# obtain the path and the revision in case of '-wc' argument
mergeSets = GetWCMergeInfo()
if(mergeSets is None):
    # there are no merges in the working copy
    sys.exit(0)

(mergeSourcePath, mergedInChangeset) = GetYoungestMergeSet(mergeSets)

# obtain log message
logData = ObtainChangesetLog(mergeSourcePath, mergedInChangeset)


if(args.debug):
    print("number of revs found: " + str(countRevisions(logData)))


# build log message header
msgTemplate = """Merged {revCount} revision(s) {revs}
from: {sourceBranch}
to  : {targetBranch}\n\n"""
msg = msgTemplate.format(
    revCount=str(countRevisions(logData)),
    revs=mergedInChangeset,
    sourceBranch=GetRelativeURL(mergeSourcePath),
    targetBranch=GetRelativeURL("./"),
    )


# build log message content, i.e. list each merge
for rev in logData.findall("./logentry/msg"):
    for line in rev.text.splitlines():
        # remove jira ID's
        line = re.sub('[a-zA-Z]{2,3}-[0-9]*', '', line)

        # cleanup mesages
        line = re.sub('[ ]*:[ ]*', '', line)
        line = re.sub('[\.]{3,}', '', line)
        line = line.strip()

        if len(line) > 0:
            msg += line + "\n"

# write commit message to file for tortoise svn to use
with open(args.messageFile, "w+t") as f:
    f.write(msg)

sys.exit(0)
