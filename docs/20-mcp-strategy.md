# MCP Strategy

## Runtime product
The product's core browser runtime must not depend on Claude Code MCP. It owns a `BrowserGateway` and initially implements it directly with Playwright.

An MCP adapter may be added later under `interfaces/mcp/` to expose safe capabilities to external agents or to consume a compatible browser service. That adapter must preserve the same typed action contracts and RunPolicy enforcement.

## Claude Code development environment
Project-scoped MCP servers are optional developer tooling. If the team chooses to add them, keep shared configuration in project `.mcp.json` and never commit secrets. MCP tools may help inspect GitHub, issues, browser state, or observability systems, but the repository must remain buildable without them.

## Rule
MCP is an integration boundary, not a domain concept.
