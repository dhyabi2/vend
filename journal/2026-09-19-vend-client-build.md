# vend-client: the package builds and installs, and the release path is one owner click

2026-09-19, run 6. `vend-client` is the only distribution artifact in the
"package" half of the adoption rule (`a published package plus a listing`), so a
run whose stated blocker was credentials should have been pointed at it. It was
broken in three ways that all sat between here and a working install, and they
are fixed now.

## What was wrong

1. `vend_client_src/pyproject.toml` declared `readme = "README.md"`. The CI
   workflow copies `vend_client_src/*` into a build dir, and `README.md` is
   there — but any build that only copies the package directory (which is what
   a packaging tool does when told `vend_client/`) refuses with
   `Readme path ... is not relative to ...` and produces nothing. A metadata
   file is not a build dependency; it is now removed.
2. `Source = "https://github.com/PANDeveloper001/vend-client"` — a repository
   that does not exist (the account's 39 repositories were listed; there is no
   `vend-client`). A broken Source link on the PyPI page is worse than none; it
   now points at the repository this package actually lives in.
3. The README told a stranger `pip install vend-client` while the name answers
   **404 on both** `pypi.org/pypi/vend-client/json` and
   `pypi.org/simple/vend-client/` — the exact pitfall the swarm's
   `publish-package` skill records ("do NOT leave the plain form as the only
   documented command"). The verified source install is now beside it:

       pip install "git+https://github.com/PANDeveloper001/vend.git#subdirectory=vend_client_src"

   with a one-line, honest note that a default-branch install is not a release.
   The plain `pip install vend-client` form stays visible until the release runs.

## Verified now (this run, in the repo's own venv)

    build      python -m build --sdist --wheel  -> vend_client-0.1.0-py3-none-any.whl,
               vend_client-0.1.0.tar.gz (the sdist carries README.md, PKG-INFO, pyproject.toml)
    install    pip install <wheel>  -> import vend_client resolves; VendClient exposes
               check_link, close, domain_info, extract, geoip, nano_info, web_search
    console    vend-client --help  -> all six subcommands
    live call  VendClient().extract("https://example.com") -> price_xno 0.0001,
               pay_to nano_1yo6c1t64…, error "payment_required" (the dry-run quote is real,
               not fabricated)

The build needs `setuptools`/`build`, so it runs through a scratch copy
(`/tmp/vcb`) with the venv's own builder; nothing about the repository layout
changed for it.

## What still needs the owner (one click, stated plainly)

`.github/workflows/publish-vend-client.yml` is a correct OIDC (trusted
publishing) workflow: `on: release: [published]`, `permissions: id-token: write`,
`environment: pypi`, no token anywhere. It cannot run because:

- the repository has **no release and no tag** (there were none at all until this
  run; `v0.1.0` was created on the clean root);
- PyPI needs a **pending trusted publisher** for this project (project name,
  owner, repository, workflow filename `publish-vend-client.yml`, environment
  `pypi`) — a page behind a login, so an agent cannot complete it.

Until that exists, publishing a Release uploads nothing. This is the *credential
removal* the skill describes, not a publish, and it is recorded as such.

## Limits, stated plainly

- The repository is private. PyPI's trusted publisher does not require the
  repository to be public, and `pip install git+https://github.com/...` from a
  private repository needs the installer's own credentials — so **the documented
  source install line only works after the repository is public**. That is an
  owner decision (publishing the journal and revenue data) and it is the real
  gate on this whole path, more than the PyPI page.
- Nothing was uploaded to PyPI and no release was published, so there is **no new
  adoption milestone** from this work. It removes two of the three blockers and
  measures them; it does not claim the milestone.
