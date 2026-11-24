#!/usr/bin/env bash
# Copy this git repo into the archive, so the catalog, code and docs survive with the models.
#
# Summary: writes the repo's full git history as a bundle, plus a plain snapshot of the
# latest commit, into <archive>/repo/. Either one is enough to restore open-models
# without GitHub or Dropbox (docs/OFFLINE.md). Run it after committing; part of the
# six-month refresh (docs/REFRESH.md step 7). Tested by tests/test_mirror_repo.py.
#
# Details:
# - open-models.bundle: `git bundle` of every branch and tag. Restore with
#   `git clone open-models.bundle open-models`. Checked with `git bundle verify` after
#   writing.
# - open-models.tar.gz: `git archive` of HEAD, i.e. the committed files only, with no
#   git history. Readable with plain `tar`.
# - MIRROR.txt: the commit and date copied, and how to restore. SHA256SUMS: hashes of the
#   three files above.
# - Only committed work is copied; uncommitted changes are not, and the script warns
#   about them. Each file is written to `<name>.partial` and renamed when complete, so a
#   failed run leaves the previous mirror intact. Nothing is deleted.
# Usage: scripts/mirror_repo.sh [repo-dir]   (default: current directory; archive from
#        $OPEN_MODELS_ARCHIVE, default /Volumes/Starfish_Prime/model-storage)
set -euo pipefail

repo=$(cd "${1:-.}" && pwd)
dest=${OPEN_MODELS_ARCHIVE:-/Volumes/Starfish_Prime/model-storage}/repo
mkdir -p "$dest"
cd "$repo"

commit=$(git rev-parse HEAD)
if [ -n "$(git status --porcelain)" ]; then
  echo "warning: uncommitted changes are not mirrored (only commit ${commit:0:7})" >&2
fi

git bundle create "$dest/open-models.bundle.partial" --all 2>/dev/null
git bundle verify "$dest/open-models.bundle.partial" > /dev/null 2>&1
mv "$dest/open-models.bundle.partial" "$dest/open-models.bundle"

git archive --format=tar.gz --prefix=open-models/ -o "$dest/open-models.tar.gz.partial" HEAD
mv "$dest/open-models.tar.gz.partial" "$dest/open-models.tar.gz"

cat > "$dest/MIRROR.txt" <<EOF
open-models repo mirror
commit: $commit
subject: $(git log -1 --format=%s)
committed: $(git log -1 --format=%cI)
mirrored: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Restore with history:  git clone open-models.bundle open-models
Files only (no git):   tar xzf open-models.tar.gz
Check these files:     shasum -a 256 -c SHA256SUMS
Then see open-models/docs/OFFLINE.md.
EOF

(cd "$dest" && shasum -a 256 open-models.bundle open-models.tar.gz MIRROR.txt > SHA256SUMS)
echo "mirrored ${commit:0:7} into $dest"
