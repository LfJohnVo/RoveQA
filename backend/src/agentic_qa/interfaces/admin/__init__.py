"""Operations that require the host, not a network request.

A second Interface/Delivery adapter beside HTTP and the CLI, and it exists because of
what is *not* here: there is no endpoint that mints an API token, and there never will
be. Issuing a credential is a host-level act — whoever has the machine has everything
anyway (ADR 0019, ADR 0020) — and drawing the boundary there means no route to leak, no
route to brute-force, and no administrative super-credential whose theft escalates from
one project to all of them.

Like every delivery adapter, this one translates and calls; it holds no rules of its own.
"""
