# Shared fixtures note

Before writing more than two Layer 2 / 3 slices that need the same
kind of mock (Sage RPC, Dexie API, TibetSwap price, coinset_client),
the next session should promote those mocks into `tests/conftest.py`
(or a dedicated `tests/fixtures/` module) so every downstream slice
can reuse them without re-inventing.

## Candidates for shared fixtures

When a slice needs any of these, factor them into shared fixtures
before your second instance of the same stub:

| Fixture name (suggested)   | Replaces                          | Used by slices |
|---------------------------|-----------------------------------|----------------|
| `mock_sage_rpc`           | wallet_sage network calls         | 02-20+, 03-*, 04-09, 07-01 |
| `mock_dexie_api`          | dexie_manager requests            | 02-06, 03-08, 04-04, 07-03 |
| `mock_tibet_price`        | price_engine's TibetSwap path     | 02-05, 02-09, 04-10, 07-04 |
| `mock_coinset_client`     | mempool + block record queries    | 02-10, 03-09, 07-01 |
| `mock_spacescan`          | spacescan proxy                   | 02-07, 02-08, 04-17 |
| `stub_wallet_balance`     | cfg-pinned XCH/CAT balance helper | Layer 2/3 anywhere balances matter |
| `in_memory_db`            | fresh SQLite per-test             | 02-30, 03-* |
| `sample_fills`            | N realistic fill rows to insert   | 02-19, 03-09, 05-13 |
| `fake_cfg_builder`        | Config() instance with LIQUIDITY_MODE etc | every slice |

## Rules

1. **First use** in a slice: inline the stub with a `# TODO promote to
   conftest` comment.
2. **Second use** in a different slice: stop. Write the stub as a
   pytest fixture in `tests/conftest.py` first, then resume the slice.
3. Fixture promotion is its own small commit: `refactor(test): promote
   X stub to shared fixture`.
4. After promotion, update this note's table with the fixture name +
   slice list.

## Why not pre-build everything now?

Premature fixture abstraction is a trap. A generic mock_dexie_api that
nobody actually uses will be wrong by the time the third slice needs
it. By promoting on the **second** use, the shape of the fixture is
driven by real requirements.

The exception: `fake_cfg_builder` is so universal it's worth seeding
now. If the next session has time, they can build it as a
`conftest.py` fixture in the first Layer 2 slice — look for
`test_liquidity_mode.py` which already has a working pattern
(`_build()` method) to lift.
