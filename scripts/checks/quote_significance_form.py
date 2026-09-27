"""quote-significance-form check — research-artifact ResearchContext check.

A quote's ``significance`` is its Key Passage heading: ONE plain sentence,
at most ``quote_entry.significance_words_max`` words, in the form "Source
(date): what the passage shows". Everything else the contributor has to say
about the passage — pairings, chronology, caveats, source-form notes — goes
in the quote's ``analysis`` field, which renders as a paragraph under the
heading (``schema-research-artifact.yaml::quote_entry``). Errors on:

  - a significance of more than one sentence;
  - a significance over the word cap (whitespace-split words — the same
    count the schema comment and the build contracts state).

Runs on every artifact type, person and event included (their significance
is artifact-only today, but the field means the same thing everywhere). The
"Source (date):" form is a contributor rule, not checked here — only
sentence count and length are mechanical.

Sentence boundaries: ``.``/``!``/``?`` (plus any closing quote or bracket),
whitespace, then a capital, digit, ``§``/``$`` or an opening quote or
bracket. A period is NOT a boundary after a known abbreviation (``U.S.``,
``Dr.``, ``No.``, ``Inc.``, ``et al.``, month abbreviations, …), a
single-letter initial (``H. E. Puthoff``) or a dotted acronym (``e.g.``,
``H.R.``) — the cases the corpus carries. An ambiguous period (an
abbreviation that also ends a sentence) is read as the abbreviation, so the
splitter never over-counts.
"""

import re

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "quote_significance_form"

# Tokens that end in a period without ending a sentence. Compared
# case-sensitively against the word before the period (sans the period).
_ABBREVIATIONS = frozenset("""
    U.S U.K U.N D.C Dr Mr Mrs Ms Messrs Prof Hon Rev Gen Col Lt Maj Capt Cmdr
    Cdr Adm Sgt Rep Reps Sen Sens Gov Pres Amb Jr Sr St Ste Mt Ft No Nos
    Inc Co Corp Ltd Bros Dept Div Assn Univ Vol vol Vols pp p Pt pt Fig fig
    Figs Ch ch Sec sec Secs Art Arts Para para Eq eq Eqs Ref ref Refs App
    Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec approx ca cf al etc vs
    v viz Stat Pub Cong Sess Ed ed Eds eds Ph.D D.Eng M.D e.g i.e a.m p.m
    H.R S.Res H.Res L.L.C
""".split())

_BOUNDARY = re.compile(r'[.!?]["”’)\]]*\s+(?=["“‘(\[]?[A-Z0-9§$])')
_WORD_BEFORE = re.compile(r"(\S+)$")


def _is_abbreviation(before):
    """True when the text before a period ends in a non-terminal token."""
    m = _WORD_BEFORE.search(before)
    if not m:
        return False
    word = m.group(1).lstrip("([\"“‘")
    if word in _ABBREVIATIONS:
        return True
    if re.fullmatch(r"[A-Z]", word):          # initial: "H. E. Puthoff"
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word):  # "e.g", "H.E", "U.S"
        return True
    return False


def sentence_count(text):
    """Number of sentences in ``text`` under the boundary rule above."""
    text = " ".join((text or "").split())
    if not text:
        return 0
    count = 1
    for m in _BOUNDARY.finditer(text):
        end = m.end()
        if end >= len(text):
            break
        if text[m.start()] == "." and _is_abbreviation(text[:m.start()]):
            continue
        count += 1
    return count


def word_count(text):
    """Whitespace-split word count — the cap's unit everywhere it is stated."""
    return len((text or "").split())


def check(ctx):
    cap = ctx.schema["types"]["research-artifact"]["quote_entry"][
        "significance_words_max"]
    for i, q in enumerate(entries(ctx.data, "quotes")):
        if not isinstance(q, dict):
            continue
        sig = q.get("significance")
        if not isinstance(sig, str) or not sig.strip():
            continue
        where = f"quotes[{i}] ({q.get('id')!r})"
        n = sentence_count(sig)
        if n > 1:
            yield Issue(
                ctx.rel, "error",
                f"{where}: significance runs to {n} sentences — the heading "
                f"is one sentence (\"Source (date): what the passage "
                f"shows\"); move the rest to the quote's `analysis`",
                check_name=CHECK_NAME,
            )
        w = word_count(sig)
        if w > cap:
            yield Issue(
                ctx.rel, "error",
                f"{where}: significance is {w} words (cap {cap}) — shorten "
                f"the heading and move the rest to the quote's `analysis`",
                check_name=CHECK_NAME,
            )
