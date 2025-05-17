# Tessera Test Suites

This repository contains heavy test harnesses, performance benchmarks, and external test vectors for validating the [Tessera](https://github.com/Chainscore/tessera) JAM client implementation.

> ⚠️ This repo is **not a Python package**. It is a test suite powered by `pytest`, intended to be run alongside the `tessera` repository via a local path dependency.

---

## 🗂️  Directory Structure

```
tessera-test-suites/
├── ext/
│   └── w3f/
│       └── safrole/
│           ├── tiny/
│           │   └── test-case-1.json
│       ├── trie/
│       └── shuffle/
│   └── jamduna/
├── harness/
│   └── w3f/
│       └── stf/
│           ├── transform/
│           │   ├── safrole.py   # Defines transform_block, transform_state, transition
│           └── test_w3f_vectors.py
│       ├── trie/
│       └── shuffle/
├── perf/              # Micro-benchmarks and perf tests
├── scripts/           # Helper scripts (e.g., vector updater)
├── vendor/            # External vector sets (added via git submodules)
├── README.md          # You are here
├── pyproject.toml     # Uses Poetry, installs tsr-py in editable mode
└── poetry.lock
```

## 🧑‍💻 Setup

Package up Tessera and install it

```commandline
git clone https://github.com/Chainscore/tessera.git
cd tessera
pip install -e .
```

YOu should see something like this:
```commandline
Installing collected packages: tessera
  Attempting uninstall: tessera
    Found existing installation: tessera 0.1.0
    Uninstalling tessera-0.1.0:
      Successfully uninstalled tessera-0.1.0
Successfully installed tessera-0.1.0
```

----
# 🧪 How to Test? 

## W3F STF Modules

To run tests for a specific STF module, such as safrole, use:

```
pytest -s -vv -q harness/w3f/stf --module safrole
```

This command:
- Runs all vector tests for the safrole STF
- Uses the default spec = tiny and pattern = *.json
- Shows verbose output (-vv) and real-time print() logs (-s)
- Strips pytest noise (-q)

We do:
- Implement transform_block, transform_state, and transition in each transform/{module}.py.
- Use to_json() or from_json() methods for serializing/deserializing custom objects.
- Use DeepDiff to get readable diffs when test vectors fail.



### 🔧 Command-Line Parameters

You can customize your test runs using the following CLI options (defined in conftest.py):

#### --module

Specifies which STF module to test.
	•	Must match the folder name in harness/w3f/stf/transform/
	•	If omitted, runs all available modules

```
--module safrole
--module accumulate
```

#### --spec

Specifies the test vector spec directory to use (tiny, full, etc).
- Path: ext/w3f/{module}/{spec}/
- Default: tiny
```
--spec tiny
--spec full
```

#### --pattern

File pattern to match test vectors.
	•	Default: "*.json"
	•	Can be used to test only specific cases:
```
--pattern skip-*.json
--pattern test-42.json
```

----

### 🧭 Examples

Run all tests across all modules:

pytest -s -vv -q harness/w3f/stf

Run tests only for accumulate with full vectors:

pytest -s -vv -q harness/w3f/stf --module accumulate --spec full

Run just one test vector file in safrole:

pytest -s -vv -q harness/w3f/stf --module safrole --pattern publish-tickets*.json

----

## PyTest Param
### -s

Enable output from print() statements (useful for debugging).

### -vv

Increase verbosity to show:
- Test names
- Param combinations (e.g., test_stf_vectors[accumulate-tiny-test42.json])

### -q

Quiet mode—removes test collection summary and extra logging.


