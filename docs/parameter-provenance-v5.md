# Unmeasured parameter-provenance candidate v5

Gemini dev experiment found T030 writes a made-up or unchanged address even
though the customer supplied no replacement. Target plus yes is not authority
for a destination the model invented. This gap is separate from the existing
confirmation/target count; the measured v1-v4 code and results stay unchanged.

`agent_v5.py` adds an exact-parameter check for the synthetic single-turn
`address to ...` syntax. Missing, vague or mismatched addresses are blocked;
unsupported natural-language forms require clarification rather than guessing.
A positive control accepts the exact requested new address. Scripted T030
attempts cannot reach the store. Malformed OABC/O123 IDs receive an invalid-ID
clarification without a model call, rather than a generic not-found answer.

Four offline regression tests cover these paths. No live v5 trial, score,
promotion or broad natural-language coverage is claimed. v5 is not selected in
the measured runner by default. T020 refund-without-amount policy is still open;
this candidate does not silently resolve it. Multi-turn approval events and
full amount/address consent semantics need a separately designed protocol.
