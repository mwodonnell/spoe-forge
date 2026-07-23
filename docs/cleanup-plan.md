# Repo Cleanup Plan

Tracking doc for the async cleanup and review findings (2026-07-22). One ticket per PR-sized
commit; status updated as tickets land.

Target end state: async only at the true I/O seam (`ForgeHandler`, `Frame.decode` stream reads,
`AgentRegistry.handle_message`, `SpoeForge` server methods, `cli.healthcheck`). Everything below —
encoders, decoders, frame payload methods, negotiation — is synchronous, matching the sans-io
pattern (h11/h2): parsing and serialization work on buffers, transport stays with the caller.

## Tickets

| # | Ticket | Status |
|---|--------|--------|
| 1 | fix: correct self-comparison in SPOP version compatibility check | merged (PR #13) |
| 2 | refactor: make SPOP decode path synchronous | merged (PR #14) |
| 3 | refactor: make SPOP encode path synchronous | in review |
| 4 | refactor: make frame construction and negotiation synchronous | todo |
| 5 | chore: fix CLAUDE.md drift and small cleanups | todo |

### 1. fix: correct self-comparison in SPOP version compatibility check
`configuration.py:48` compares `floor(float_ha_ver)` to itself, so the major-version guard never
fires and any HAProxy version >= 2.0 is accepted (e.g. a future "3.1"). Fix the left side to
`floor(float_ver)` and add regression tests (`["3.0"]` alone must be incompatible, `["2.5"]`
compatible).

### 2. refactor: make SPOP decode path synchronous
De-async `spop/decoders/data_types.py` and `spop/decoders/payloads.py`, the `decode_payload`
methods on all frame subclasses, and `Frame.decode` internals (`Frame.decode` itself stays async —
it owns the `reader.readexactly` calls). Includes two small fixes in the same path:
- drop the wrong-shaped/redundant `if len(buf) == end + 1` empty-action-list special case in
  `decode_list_of_actions`
- `decode_metadata` bounds check `end >= len(buf)` should be `>`

Update decoder/roundtrip tests to sync.

### 3. refactor: make SPOP encode path synchronous
De-async `spop/encoders/data_types.py` and `spop/encoders/payloads.py`, the `encode_payload`
methods, `Frame.encode`, and call sites in `server/handler.py` and `cli.py`. Update encoder and
roundtrip tests.

### 4. refactor: make frame construction and negotiation synchronous
De-async `Frame.construct`, `construct_payload` methods, `Frame.get_frame_class`, and all of
`ServerConfiguration`; update call sites (`handler.py`, `cli.py`). Remove dead
`AgentRegistry._validation_cache`. Update tests.

### 5. chore: fix CLAUDE.md drift and small cleanups
- CLAUDE.md: default max frame size is 4096 (doc says 16384); remove references to nonexistent
  `sample_server.py`
- `cli.py`: move module-level `create_logger()` call into `main()` (import side effect)
- `frame.py`: `engine_id: str = None` -> `str | None`; `typing.Type`/`Callable` -> `type[...]` /
  `collections.abc.Callable`
- `context.py`: `get_arg` try/except -> `dict.get`
- `spop_types.py`: docstring says "Pydantic models"; they are dataclasses
- `spoe_forge.py`: drop unnecessary `if handler_actions:` guard before `extend`

## Deferred / not planned
- Docstring thinning (most restate signatures): cosmetic, churn-heavy — only if explicitly
  requested.
