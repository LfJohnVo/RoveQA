"""Telling a wall apart from a page that merely mentions signing in.

Half the value of this module is what it must *not* match. A deterministic check that
fails reports `FailureKind.PRODUCT`, which is the only kind that produces `failed`, and
downgrading it to `SESSION` is how a real defect gets excused. So every false positive
here is a bug that hides bugs — the worst kind this project can ship.

The other half is the case the Phase 17 gate found by running: an application's protected
page often renders "Please sign in" rather than a login form, and a first version of this
that required a password field walked straight past it.
"""

import pytest

from agentic_qa.domain.browser.authentication import looks_like_sign_in
from agentic_qa.domain.exploration.state import Affordance, PageState


def page(*, title: str = "", text: str = "", offers: tuple[str, ...] = ()) -> PageState:
    return PageState(
        url="https://app.test/dashboard",
        title=title,
        body_text=text,
        affordances=tuple(Affordance(role="textbox", name=name) for name in offers),
    )


class TestAWallIsRecognised:
    def test_a_page_that_renders_a_login_form(self) -> None:
        assert looks_like_sign_in(
            page(title="Sign in", text="Sign in to Acme", offers=("Email", "Password"))
        )

    def test_a_protected_page_that_only_says_so(self) -> None:
        # The case the gate found. No form, no password field — just a refusal, which is
        # what many applications render on a route you are not entitled to.
        assert looks_like_sign_in(page(title="Sign in", text="Please sign in"))

    @pytest.mark.parametrize(
        "text",
        [
            "Please log in to continue",
            "You must sign in to view this page",
            "Sign in required",
            "Your session has expired",
            "Access denied",
            "Authentication required",
            "Unauthorized",
            "Debes iniciar sesión para continuar",
            "Acceso denegado",
            "Tu sesión ha caducado",
            "Sesión expirada",
        ],
    )
    def test_the_things_a_page_says_when_it_turns_you_away(self, text: str) -> None:
        assert looks_like_sign_in(page(text=text))

    def test_a_spanish_login_form(self) -> None:
        assert looks_like_sign_in(
            page(title="Acceder", text="Inicia sesión", offers=("Correo", "Contraseña"))
        )


class TestAPageIsNotAWall:
    def test_a_marketing_page_with_a_log_in_link_in_its_header(self) -> None:
        # The most common page on the web. Matching the words "log in" would excuse a
        # real defect on every one of them.
        assert not looks_like_sign_in(
            page(
                title="Acme — Mission control for IT",
                text="Home  Products  Pricing  Log in  Book a demo\nWe monitor your systems.",
            )
        )

    def test_a_password_change_form_inside_a_signed_in_application(self) -> None:
        # It has a password field and it is not a wall: you are already through.
        assert not looks_like_sign_in(
            page(
                title="Account settings",
                text="Change your password",
                offers=("Current password", "New password"),
            )
        )

    def test_a_page_about_authentication_as_a_topic(self) -> None:
        assert not looks_like_sign_in(
            page(title="Docs — Authentication", text="How our authentication works, in depth.")
        )

    def test_an_ordinary_page_that_simply_lacks_the_literal(self) -> None:
        # The case that must keep accusing the product, because it is the product.
        assert not looks_like_sign_in(page(title="Dashboard", text="Nothing to report today."))

    def test_a_page_offering_a_password_field_and_nothing_about_signing_in(self) -> None:
        # Half the signal is not the signal.
        assert not looks_like_sign_in(page(title="Setup", offers=("Password",)))

    def test_an_empty_page(self) -> None:
        assert not looks_like_sign_in(page())
