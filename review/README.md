# Loam's Market reviewer

Every pull request that adds a listing, moves one to a new version or removes
one is reviewed here by itself, with no person in the path. A pass merges; a
refusal says why on the request. This folder is the whole reviewer:

| file | what it is |
|---|---|
| `STANDARDS.md` | the page a listing must meet; given to the model word for word, and the page a maker reads |
| `INSTRUCTIONS.md` | what the model is told it is and what it answers; `STANDARDS.md` is put into it |
| `config.json` | the model (one line), the pinned Loam release (`version` and `commit`) whose manifest reader is used, and every limit |
| `prepare.py` | every check that needs no model, then the packet the model reads |
| `review.py` | one model run, its answer held to a fixed shape |
| `decide.py` | comments, and on a pass merges and writes Loam's note |
| `test_review.py` | the offline checks: `python3 review/test_review.py` |
| `proof.py` | the live proof runner: `python3 review/proof.py` over `proof/` |
| `proof/` | synthetic plugin fixtures and `manifest.json` exercised on every change to the reviewer |
| `proof_dedupe.py` | skips a duplicate push proof run when a same-repo PR already proved the identical reviewer tree |
| `loam_pin.py` | resolves Loam `x.y.z` release tags and updates `config.json` to a named release commit |
| `../.github/workflows/review.yml` | the three jobs that review listing pull requests |
| `../.github/workflows/review-tests.yml` | offline unit tests and manifest checks against the pinned Loam release |
| `../.github/workflows/review-proof.yml` | runs `proof.py` through the real model and `decide.py` on every change to the reviewer |
| `../.github/workflows/loam-pin.yml` | scheduled safety-net follower that moves the Loam pin after passing tests and proof |

## The path of a request

1. **`pull_request_target`** fires on opened, synchronize and reopened, for
   a branch or a fork alike. It runs the workflow, this folder and
   `build.py` as they are on `main`, never as the request has them. Nothing
   from the request is checked out or run.
2. **`gate`** (read-only token, no model key) runs `prepare.py github`:
   - the request's file list, from the API: exactly one file,
     `listings/<id>.json`, added, modified or removed. Anything else is
     refused without a model call;
   - the listing at the request's head, read from the API as text, checked by
     `build.py`'s own rules;
   - the link: the repository is public; the ref is a tag of that repository,
     or a whole commit one of its own tags names (from `git ls-remote`, which
     lists the repository's refs and never a fork's); never a branch. The
     commit is fixed here, once;
   - the maker: the request comes from the repository's owner, a public member
     of the organisation that owns it, or a maintainer; an existing listing is
     not moved to another repository;
   - no limit on submissions: every push is reviewed, as often as a maker likes;
   - the plugin: the repository's tarball at that commit, unpacked as plain
     files (no symlinks, nothing outside); Loam's own manifest reader
     (`lib/loam_plugins.py` at the release commit in `config.json`) reads its
     `PLUGIN.md` as an install would; `touches` must be written; compiled,
     minified or binary-but-not-a-picture files are refused (the standards
     page asks for source a person can read);
   - for a new version, the version last reviewed (its commit from
     `notes/<id>.json`) is fetched too, and the packet carries what the new one
     declares beyond it and the diff;
   - the one bound: what the model can read at once (`context_bytes`, about
     2.5 MB of text). A diff that does not fit is left out first; a plugin
     that alone does not fit is refused with what to do about it;
   - a scan for facts, not verdicts: hosts named in code against those
     declared, code that runs code, words about logins and keys, and
     `steering_leads` (lines mentioning reviewers, models, assistants,
     verdicts or `ignore ...`, ordered with strong steering phrasing first).
3. **`review`** (no GitHub permission beyond reading this public repository;
   the model key and nothing else) runs `review.py`: one request to the model,
   no history, instructions and standards from `main` as the system
   instruction, the packet as one message between two lines of a random
   boundary it is told is data. The answer is asked for as JSON in a fixed
   schema, then held to it again here: a verdict of `pass` or `refuse`,
   reasons, questions, Loam's note, whether the declaration matches the code,
   and `steering_lead_rulings` — an explicit `{at, steers_review, why}` ruling
   on every entry in `scan.steering_leads`. A pass that carries a question, a
   reason, a mismatch or any `steers_review: true` ruling becomes a refusal.
   Anything else is an `error`.
4. **`decide`** (write permission, no model key) runs `decide.py`. It reads
   `action` and `verdict`, which are closed sets, and nothing else as an
   instruction. On a pass, it verifies that no steering ruling was `true` and
   that every `scan.steering_leads` entry has an explicit `steers_review: false`
   ruling (an omitted lead fails closed as `error` and merges nothing). There
   is no word-list overrule: honest plugins that mention LLMs, language models,
   assistants, code reviewers or cache invalidation pass once the model rules
   those lines benign, while actual steering attempts are refused on sight. It
   comments (all model and maker text escaped: no mentions, no HTML, no
   images). On a pass it merges the request through the API **at the head
   commit the gate read**, so a push after the review cannot be merged, then
   writes `notes/<id>.json` and rebuilds `list.json` on `main`. A refusal or
   an error is a red check and nothing merges.
5. **`build.py`** puts a listing in `list.json` only when `notes/<id>.json` is
   for its exact `link`, and then with `review`: the commit, the folder and
   Loam's note. No hand edit lists what the reviewer did not pass. Every Loam
   reads and installs a listing at `review.commit`, so a tag moved later
   delivers nothing new.

## When the reviewer is fooled

The plugin's own text reaches the model, and some of it will be written to
fool it. Assume it sometimes succeeds. What a fooled model can do:

- **Pass a bad listing.** That is the risk that is left. It is narrowed by
  the checks that need no model (they cannot be talked to), by requiring an
  explicit per-lead ruling on every scanned steering lead before `decide.py`
  will merge, by the proof set run on every change to the reviewer, and by
  the note and Loam's own install declaration, which owners read before
  saying yes. A fixed word-list overrule is deliberately not used here:
  because `prepare.py` is public, a regex backstop is trivial for a real
  adversary to evade while routinely refusing honest AI plugins.
- **Not reach anything else.** It has no tools and no network. Its answer is a
  JSON object that a program holds to a schema. It never sees a token: the
  model key is in `review`'s environment only, and that job cannot write to
  GitHub. The job that can write never sees the model key and never runs the
  request's code.
- **Not change what it is judged by.** The workflow, `STANDARDS.md` and
  `INSTRUCTIONS.md` come from `main`; a request that touches them (or anything
  but its own listing) is refused before a model is asked.
- **Not merge anything it was not shown.** The merge names the reviewed head;
  the listing delivers the reviewed commit.

**Why `pull_request_target`, and why it is safe here.** A fork's request run by
`pull_request` gets no secrets and a read-only token, so it could not call
the model or comment. The usual way around that, `pull_request_target`,
runs with the base repository's secrets and write token, and people get hurt
when such a workflow checks out the request's code and runs it (a build, a
test, an install script): the stranger's code then holds the keys. This
workflow never checks out or runs the request's code: it reads one JSON file
through the API and downloads the plugin as a tarball it only reads. The
other known trap, passing data from an unprivileged run to a privileged one
through artifacts (`workflow_run`), does not arise: every artifact here is
written by this workflow's own steps in the same run. And no `${{ }}`
expression puts request text into a shell line.

## Keeping the Loam pin current

`config.json` pins `loam.version` and `loam.commit` to a named Loam release
tag (never `main` or a moving branch), so the reviewer parses manifests with
a release owners can actually run.

- When a Loam release is cut (`lib/loam_worktree.py` or `bin/sign-release` in
  `loamhq/loam`), `lib/loam_marketplace_pin.py` opens a branch pull request
  here updating `review/config.json`, waits for both `review-tests` and
  `review-proof` to pass, and merges it. If either fails, the pull request
  stays open, `main` is unchanged, and the release reports the failure loudly.
- As a safety net for release tags pushed outside that path,
  `.github/workflows/loam-pin.yml` checks `loamhq/loam` on a schedule (and on
  manual dispatch), runs the offline tests and full proof set in read-only
  jobs before pushing, and opens an issue if a pin move fails. `review.yml`
  gains no permissions or triggers for this.

## The proof set

Every change to `review/**`, `build.py` or the reviewer workflows runs both
`review-tests.yml` (offline unit checks and manifest parsing against the
pinned Loam release) and `review-proof.yml` (the full proof set in
`review/proof/` through the real model and `decide.py`).

- **Fork isolation:** `review-proof.yml` triggers on `pull_request` (never
  `pull_request_target`) and refuses fork pull requests without ever exposing
  `LOAM_REVIEW_GEMINI_KEY`. Reviewer changes come from branches of this
  repository.
- **One round per change:** Each proof case runs once (~$0.25 total on Gemini
  4 Argon for 17 cases). If a case flips, only that case runs two confirmation
  rounds to show whether the failure is solid or flaky, and the check still
  fails. On `push` to `main`, `proof_dedupe.py` skips a duplicate run when the
  exact reviewer tree already passed `proof` on its merged same-repo pull
  request.
- **Public fixtures:** The synthetic fixtures in `review/proof/cases/` are
  public so contributors can run and verify the regression suite locally. They
  are a regression gate, not a substitute for occasional held-out adversarial
  testing.

## Money

There is no limit on submissions: every push is reviewed. A review of a
theme costs about $0.04 and of a larger extension about $0.10 to $0.20 at
current prices for Gemini 4 Argon (about twice that after Google's price
change of 1 December 2026). The largest possible review, a plugin filling the
model's context, is a few dollars. A full 17-case proof-set run costs about
$0.25. A spend alert on the key's project (not a cap) is the cheap way to see
unusual use.

## Running it

- **The key** is the repository secret `LOAM_REVIEW_GEMINI_KEY`, read by the
  `review` job (and the read-only `proof` jobs) alone. The model is `model`
  in `config.json`.
- **A review that could not finish** (the model unreachable, an answer out of
  shape, or an unaccounted steering lead) merges nothing and says so; push
  again or re-run the workflow.
- **`review/kept.json`** holds the listings that were on the list before the
  reviewer was switched on (2026-11-19) and that its first review refused.
  Each stays listed exactly as it was, at that link and without a note, until
  a new version passes; then its entry no longer matters and may be removed.
  Nothing is ever added to it, and no pull request can change it.
- **The tests:** `python3 review/test_review.py`, `python3 test_downloads.py`,
  `python3 review/proof.py --offline-only`, and (with `GEMINI_API_KEY`)
  `python3 review/proof.py`.

The gate reads GitHub’s asset metadata for the resolved tag. It records the
fixed-name tar file’s SHA-256 beside the reviewed commit and folder. Neither
the model nor a maker’s listing supplies these fields. Loam verifies both the
file checksum and the installed tree against its own reviewed Git checkout.

The downloads workflow runs on a schedule or a manual dispatch on main. It
reads release metadata and commits only `stats.json`. Each GitHub asset ID
retains its highest observed counter, including after deletion. Replacement
assets get new IDs. A failed collection publishes nothing. Stats-only
commits do not match the reviewer’s listing path filter. Pull-request checks
have read permission and the review gate accepts a single listing file.
