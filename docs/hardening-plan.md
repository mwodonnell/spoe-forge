# Hardening Plan

Tracking doc for findings from an external code audit (2026-07-23, post v0.0.4). All headline
bugs were independently reproduced before being recorded here. Same workflow as the async
cleanup: one ticket per PR-sized commit, statuses updated as they land. This doc (and
`docs/cleanup-plan.md`) get deleted in the final ticket — tracking docs don't outlive the work
(mjo, 2026-07-23).

Theme: trust the wire and the user less. The codec and layering are sound; the gaps are at the
robustness boundary (unbounded input, charset assumptions, silent truncation, handler failures).

## Tickets (in working order)

| # | Ticket | Status |
|---|--------|--------|
| 1 | fix: enforce max frame size on inbound frames | merged (PR #20) |
| 2 | fix: validate non-ASCII vs HAProxy, then latin-1 if confirmed | merged (PR #21) — validated: HAProxy ships raw bytes |
| 3 | fix: range-check integer encoders | merged (PR #22) |
| 4 | feat: support async message handlers | merged (PR #23) |
| 5 | fix: keep decode errors within SpopDecodeError contract | merged (PR #24) |
| 6 | refactor: Messages as ordered sequence (match SPOA prior art) | merged (PR #25) |
| 7 | fix: compare SPOP versions as (major, minor) tuples | in review (bundled PR) |
| 8 | fix: handler failures ACK empty instead of disconnecting | in review (bundled PR) |
| 9 | feat: public serve(), ssl passthrough, clean shutdown | todo |
| 10 | chore: packaging fixes + delete tracking docs | todo |

### 1. fix: enforce max frame size on inbound frames
`Frame.decode` reads a 4-byte length then `readexactly(frame_len)` with no upper bound — a
misbehaving peer can claim a ~4 GiB frame and the agent buffers it (memory DoS). Enforce the
negotiated `max_frame_size` on decode; pre-handshake, cap at the agent's configured max (spec is
silent on a pre-handshake limit; a real HELLO is ~200 bytes). Disconnect with `FRAME_TOO_BIG`
(code 3). Included: when an outbound ACK exceeds the negotiated size, send
`AGENT_DISCONNECT FRAME_TOO_BIG` instead of silently closing (today HAProxy's stream hangs until
its processing timeout).

### 2. fix: validate non-ASCII vs HAProxy, then latin-1 if confirmed
`decode_string`/`encode_string`/`encode_dt_string` use ASCII and raise on any byte >= 0x80,
tearing down the whole connection with PROTOCOL_ERROR. ASCII was a deliberate original choice —
the spec doesn't specify STRING encoding (decode_string's docstring records this). **Step 1 is
validation** (mjo, 2026-07-23): use the docker harness to route a request with non-ASCII header
bytes through HAProxy into a message arg and observe what arrives at the agent. Only if HAProxy
ships raw bytes >= 0x80 do we switch to latin-1 (lossless byte<->str, h11's prior art for HTTP
headers); if HAProxy sanitizes them itself, close as no-work-needed.

### 3. fix: range-check integer encoders
The `try/except ValueError` guards around `ctypes.c_uint32/c_uint64` are dead code — ctypes masks
out-of-range ints instead of raising. Reproduced: `encode_dt_int64(2**70)` silently encodes 0.
Validate ranges explicitly and raise `SpopEncodeError`.

### 4. feat: support async message handlers
`AgentRegistry.handle_message` always wraps in `asyncio.to_thread`. An `async def` handler returns
an unawaited coroutine, fails the `isinstance(..., list)` check, and kills the connection with a
confusing error. Reproduced. Fix: `inspect.iscoroutinefunction(handler)` -> await directly, else
`to_thread` (the Starlette/FastAPI pattern). Widen `MessageHandlerFunc` to allow awaitable
returns; update README/CLAUDE.md "synchronous handlers only" status lines.

### 5. fix: keep decode errors within SpopDecodeError contract
`decode_list_of_actions` indexes `buf[offset]` directly; on truncated input a raw `IndexError`
escapes (reproduced), which `core_handler` won't catch — breaking the invariant that all malformed
input surfaces as `SpopDecodeError`. Add bounds checks; also validate the NB-ARGS byte against
`ActionNBArgs` instead of skipping it.

### 6. refactor: Messages as ordered sequence (match SPOA prior art)
`Messages` is a dict keyed by message name, so a repeated message in one NOTIFY silently
overwrites the first. Prior art checked (2026-07-23): negasus/haproxy-spoe-go models messages as
a slice, criteo/haproxy-spoe-go streams a MessageIterator — neither keys by name or dedups.
Decision (mjo, 2026-07-23): follow prior art — `Messages` becomes an ordered list of
(name, args) pairs. Blast radius is internal (decode/encode, `_notify_handler`, Notify frame,
tests); user handlers receive per-message contexts and are unaffected.

### 7. fix: compare SPOP versions as (major, minor) tuples
`_check_version_compatibility` compares via `float()`; `float("2.10")` == 2.1, so a double-digit
minor version would mis-order. Parse "Major.Minor" into int tuples. (mjo, 2026-07-23: fix now.)

### 8. fix: handler failures ACK empty instead of disconnecting
Today any handler exception -> `SpoeAgentError` -> AGENT_DISCONNECT, collaterally killing all
in-flight streams on the connection. New default: log the exception and ACK with zero actions —
HAProxy's var-absence and on-error machinery handles the rest (the standard framework pattern: a
handler 500 doesn't kill the worker). No config knob — single behavior, per the simplicity rule.
Protocol-level errors (SpopDecodeError etc.) still disconnect as before.

### 9. feat: public serve(), ssl passthrough, clean shutdown
- Expose `async def serve(host, port)` so the agent can run inside an existing event loop;
  `run()` becomes a thin `asyncio.run(self.serve(...))` wrapper
- Pass `ssl=` through to `asyncio.start_server` for TLS between HAProxy and the agent
- Catch KeyboardInterrupt in `run()` for a clean shutdown message instead of a traceback

### 10. chore: packaging fixes + delete tracking docs
- Add `spoe_forge/py.typed` (and packaging inclusion) so consumers' type checkers see the hints
- Align ruff pins: pyproject has 0.14.2, `.pre-commit-config.yaml` has v0.9.9
- Delete `docs/cleanup-plan.md` and this file — the batch is done

## Open decisions (need mjo)

None — all resolved.

## Queued design round (after this batch)

- **Concurrent pipelining**: capability is negotiated but `core_handler` is serial — one slow
  handler head-of-line-blocks every stream on the connection. Design pass needed: task-per-NOTIFY,
  writer lock, out-of-order ACKs (spec-legal — ACKs echo stream/frame ids). Also soften the
  misleading comment in `_find_common_capabilities`. (mjo, 2026-07-23: queued for after cleanup.)

## Rejected audit suggestions

- **Trove classifier -> Beta**: Prod/Stable was deliberate (PR #10) and the library is
  production-deployed. Old PyPI releases carrying an Alpha classifier are immutable upload-time
  metadata, not drift.
- **Move tracking to GitHub issues**: in-repo docs are the established workflow; they get deleted
  at batch end instead.
- **AgentContext `ctx["src"]` sugar**: duplicates get_arg/has_arg for zero new capability
  (mjo, 2026-07-23: skip).
