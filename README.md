# Tessera Test Suites

This repository contains heavy test harnesses, performance benchmarks, and external test vectors for validating the [Tessera](https://github.com/Chainscore/tessera) JAM client implementation.

> ⚠️ This repo is **not a Python package**. It is a test suite powered by `pytest`, intended to be run alongside the `tessera` repository via a local path dependency.

---

## 🗂️ Structure

```bash
tessera-test-suites/
├── ext/               # External test vectors
│   └── w3f/           # W3F Test Vectors
│   └── jamduna/       # Jam Duna Testnet data
├── harness/           # Test drivers consuming external vector files
│   └── test_w3f.py    # Example test using Web3 Foundation vectors
├── perf/              # Micro-benchmarks and perf tests
├── scripts/           # Helper scripts (e.g., vector updater)
├── vendor/            # External vector sets (added via git submodules)
├── README.md          # You are here
├── pyproject.toml     # Uses Poetry, installs tsr-py in editable mode
└── poetry.lock
