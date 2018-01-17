# requirements

python six package

```
$ pip install six
```

# start-commit.py
commit hook to auto generate a merge message

![](docs/start-commit-example.png)

It will list:
* Revision count
* Revision list
* Source branch
* Target branch
* Sanitized commit messages of merged commits:
* Remove empty lines
* Remove jira ID’s to prevent the svn tab in jira from picking up all merges!
* …


Not yet supported:
* Reverse merges 
* Mixed merges (merges and reverse merges combined)


## configuration

![](docs/start-commit-config.png)

* hook type = Start Commit Hook

execute the script when starting a new commit. so that a custom commit message is generated based on the working copy changes.

* working copy path = D:/dev/

the hook is only used when the actual svn working copy is included in this path.  I.e. set different hook scripts for each repo or enable the hookscript for all svn working copies in that location.

* Command Line To Execute = `python <path to git repo>/start-commit.py`

the script to execute, i.g. start-commit.py





