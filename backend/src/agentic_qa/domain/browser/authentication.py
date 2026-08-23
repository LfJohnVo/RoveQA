"""Telling "we are not signed in" apart from "the product is broken".

The gate for Phase 17 found this by running it. A story asked the fixture's `/dashboard`
for the words "Signed in". Without a session the page answers 200 and renders a login
prompt instead — behaving exactly as designed — so the literal is genuinely absent, the
deterministic check reports absence, and absence reports `FailureKind.PRODUCT`. The run
came back **`failed`**: an accusation against a correct application, which is the one
outcome this project treats as unrecoverable, because a report that has cried wolf once
is read with suspicion forever (docs/00).

Everything here is shaped by one asymmetry: a false negative costs a confusing report,
and a false positive **excuses a real defect**. So the signals are narrow, and each one
is something only a page turning you away actually does.

Two of them, because protected pages come in two shapes. Some render the login form —
recognised by a password field *and* sign-in wording, never either alone, since a
password-change screen inside a signed-in application has the field and a marketing
header has the wording. Others render only a refusal — "Please sign in", "Session
expired" — recognised by phrases rather than words, because half the web has a `Log in`
link and matching it would start excusing defects on all of them.

What this deliberately does not catch: a wall that neither asks for a password nor says
why — an SSO redirect, a magic-link screen, a bare 403 page. An off-origin redirect is
already refused by the policy and reported as such; the rest stay a known gap rather
than a guess.
"""

import re

from agentic_qa.domain.exploration.state import PageState

_PASSWORD_FIELD = re.compile(
    # English, Spanish, Portuguese, French, German — the languages a self-hosted tool
    # meets first. A field named for a password is the structural half of the signal.
    r"\b(password|passphrase|contrase(ñ|n)a|senha|mot\s+de\s+passe|kennwort|passwort)\b",
    re.IGNORECASE,
)

_SIGN_IN_CONTEXT = re.compile(
    r"\b("
    r"sign\s?in|signin|log\s?in|login|authenticat\w*"
    r"|inicia\w*\s+sesi(ó|o)n|acced\w+|autentic\w+"
    r"|conecta\w*|anmeld\w+|connexion|entrar"
    r")\b",
    re.IGNORECASE,
)
"""The other half, and only ever read together with the first.

Either alone is a false positive waiting to happen: a password-change form inside a
signed-in application has a password field and is not a wall, and a page with a "Log in"
link in its header is not one either.
"""


_DEMAND = re.compile(
    r"("
    r"please\s+(sign|log)\s?in"
    r"|you\s+(must|need\s+to|have\s+to)\s+(sign|log)\s?in"
    r"|(sign|log)\s?in\s+(to\s+continue|required|to\s+view|to\s+access)"
    r"|(session\s+(has\s+)?expired|your\s+session\s+ended)"
    r"|(unauthori[sz]ed|access\s+denied|not\s+authenticated|authentication\s+required)"
    r"|(inicia|iniciar)\s+sesi(ó|o)n\s+para"
    r"|debes\s+(iniciar\s+sesi(ó|o)n|autenticarte)"
    r"|(acceso\s+denegado|no\s+autorizado)"
    # `(ha\s+)?` because both spellings are ordinary: "sesión expirada" on a banner
    # and "tu sesión ha caducado" in a sentence. The stem match takes the gender and
    # number with it.
    r"|sesi(ó|o)n\s+(ha\s+)?(expirad|caducad|finalizad)\w*"
    r")",
    re.IGNORECASE,
)
"""A demand addressed to the visitor, and phrases rather than words on purpose.

The first version of this module required a password field, and the Phase 17 gate showed
why that is not enough: an application's protected page often does not *render* the login
form, it renders "Please sign in". No password field anywhere, and the run went on to
accuse the product.

Widening to the word "sign in" would have been the easy fix and the wrong one — half the
web has a `Log in` link in its header, and matching it would start excusing real defects.
A phrase like "please sign in" or "session expired" is something only a page turning you
away actually says.
"""


def looks_like_sign_in(page: PageState) -> bool:
    """Whether this page is turning the visitor away for want of a session.

    Two shapes, because protected pages come in two:

    - **It offers somewhere to type a password** *and* talks about signing in. The login
      form itself. Either half alone is a false positive waiting to happen — a
      password-change form inside a signed-in application has the field and is not a
      wall, and a header with a `Log in` link is not one either.
    - **It makes a demand**: "please sign in", "session expired", "access denied". No
      form, just a refusal, which is what many applications render on a protected route.
    """
    text = f"{page.title or ''}\n{page.visible_text}"
    if _DEMAND.search(text):
        return True
    asks_for_a_password = any(
        _PASSWORD_FIELD.search(affordance.name) for affordance in page.affordances
    )
    return asks_for_a_password and bool(_SIGN_IN_CONTEXT.search(text))
