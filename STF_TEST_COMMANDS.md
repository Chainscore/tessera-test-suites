# STF Test Commands

Run these from the repo root:

`/home/darkknight/Chainscore Labs/Tesseract/tessera-main`

## Run All Tiny JSON STF Modules

Script:

```bash
./scripts/run-stf-tiny-verbose.sh
```

This runs all STF modules with `-s -vv`, so each module and each vector case is printed.

One-liner:

```bash
for m in assurances authorizations history preimages safrole reports statistics disputes accumulate; do
  echo "== $m =="
  ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "$m" --spec "tiny" --pattern "*.json" -s -vv --no-rpc || break
done
```

## Run One Module

Template:

```bash
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "<module>" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
```

## Per-Module Tiny JSON Commands

```bash
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "assurances" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "authorizations" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "history" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "preimages" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "safrole" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "reports" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "statistics" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "disputes" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "accumulate" --spec "tiny" --pattern "*.json" -s -vv --no-rpc
```

## Full Spec Variant

```bash
SPEC=full ./scripts/run-stf-tiny-verbose.sh
```

Or for one module:

```bash
ASYNC=1 JAM_LOG_LEVEL=debug uv run pytest test-suites/harness/w3f/stf/test_w3f_vectors.py --module "reports" --spec "full" --pattern "*.json" -s -vv --no-rpc
```

## Script Overrides

The script supports environment overrides:

```bash
SPEC=full ./scripts/run-stf-tiny-verbose.sh
PATTERN="report*.json" ./scripts/run-stf-tiny-verbose.sh
JAM_LOG_LEVEL=info ./scripts/run-stf-tiny-verbose.sh
```
