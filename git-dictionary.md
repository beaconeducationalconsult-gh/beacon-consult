# Git Command Dictionary

A quick-reference guide to common Git commands, grouped by purpose, each with an example.

---

## Setup & Configuration

### `git config`
Sets configuration values like your name, email, or editor.
```bash
git config --global user.name "Jane Doe"
git config --global user.email "jane@example.com"
```

### `git init`
Creates a new, empty Git repository in the current directory.
```bash
git init my-project
```

### `git clone`
Copies (clones) an existing remote repository to your local machine.
```bash
git clone https://github.com/user/repo.git
```

---

## Tracking Changes

### `git status`
Shows the state of the working directory and staging area (what's changed, staged, or untracked).
```bash
git status
```

### `git add`
Stages changes, preparing them to be committed.
```bash
git add index.html          # stage a single file
git add .                   # stage everything in the current directory
```

### `git commit`
Records staged changes as a new commit in the repository's history.
```bash
git commit -m "Add navigation bar"
```

### `git diff`
Shows the differences between commits, the working directory, and the staging area.
```bash
git diff                    # unstaged changes
git diff --staged           # staged changes not yet committed
```

### `git rm`
Removes a file from the working directory and stages the deletion.
```bash
git rm old-file.txt
```

### `git mv`
Renames or moves a file and stages the change.
```bash
git mv old-name.txt new-name.txt
```

---

## Viewing History

### `git log`
Shows the commit history.
```bash
git log                     # full history
git log --oneline --graph   # compact view with branch graph
```

### `git show`
Displays details (metadata and diff) of a specific commit.
```bash
git show a1b2c3d
```

### `git blame`
Shows who last modified each line of a file, and in which commit.
```bash
git blame README.md
```

---

## Branching & Merging

### `git branch`
Lists, creates, or deletes branches.
```bash
git branch                  # list branches
git branch feature-login    # create a new branch
git branch -d feature-login # delete a branch
```

### `git checkout`
Switches branches or restores files. (Largely superseded by `switch`/`restore` in modern Git.)
```bash
git checkout feature-login          # switch to a branch
git checkout -- index.html          # discard local changes to a file
```

### `git switch`
Switches between branches (modern replacement for part of `checkout`).
```bash
git switch main
git switch -c new-feature   # create and switch to a new branch
```

### `git restore`
Restores working directory files to a previous state (modern replacement for part of `checkout`).
```bash
git restore index.html              # discard unstaged changes
git restore --staged index.html     # unstage a file
```

### `git merge`
Combines changes from one branch into the current branch.
```bash
git switch main
git merge feature-login
```

### `git rebase`
Reapplies commits from your branch on top of another branch, creating a linear history.
```bash
git switch feature-login
git rebase main
```

### `git cherry-pick`
Applies a specific commit from one branch onto another.
```bash
git cherry-pick a1b2c3d
```

---

## Working with Remotes

### `git remote`
Manages connections to remote repositories.
```bash
git remote add origin https://github.com/user/repo.git
git remote -v                # list remotes
```

### `git fetch`
Downloads commits and refs from a remote without merging them.
```bash
git fetch origin
```

### `git pull`
Fetches from a remote and merges (or rebases) into the current branch.
```bash
git pull origin main
git pull --rebase origin main
```

### `git push`
Uploads local commits to a remote repository.
```bash
git push origin main
git push -u origin feature-login    # push and set upstream tracking
```

---

## Undoing Changes

### `git reset`
Moves the current branch pointer, optionally changing staged/working files.
```bash
git reset --soft HEAD~1     # undo last commit, keep changes staged
git reset --hard HEAD~1     # undo last commit, discard all changes
```

### `git revert`
Creates a new commit that undoes the changes from a previous commit (safe for shared history).
```bash
git revert a1b2c3d
```

### `git clean`
Removes untracked files from the working directory.
```bash
git clean -n                 # preview what would be deleted
git clean -f                 # actually delete untracked files
```

---

## Temporary Storage

### `git stash`
Temporarily shelves uncommitted changes so you can work on something else.
```bash
git stash                    # stash current changes
git stash list                # list stashes
git stash pop                 # reapply and remove the most recent stash
```

---

## Inspecting & Comparing

### `git tag`
Marks specific commits, often used for releases.
```bash
git tag v1.0.0
git tag -a v1.0.0 -m "First release"
```

### `git bisect`
Uses binary search through commit history to find which commit introduced a bug.
```bash
git bisect start
git bisect bad                # current commit is broken
git bisect good v1.0.0         # this earlier commit was fine
```

---

## Tip: Getting Help
```bash
git help commit
git commit --help
```

Both open detailed documentation for a specific command.
