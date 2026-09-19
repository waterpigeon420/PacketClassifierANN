# packetClassifier

End-to-end pipeline for benchmarking 5-tuple packet classifiers: generate a
realistic ruleset + matching packet trace with ClassBench-ng, then classify
either with the C++ classifier in `network-packet-classification` or the
Python pipeline for fast iteration. Runs in Docker so nobody has to install
Ruby/CMake/build tools on their own machine.

## Layout

- `classbench-packet-classification/` -- [ClassBench-ng](https://github.com/classbench-ng/classbench-ng),
  generates synthetic IPv4/IPv6/OpenFlow 5-tuple rulesets from real-world-derived
  seed profiles, plus the original ClassBench `db_generator`/`trace_generator`
  C++ tools it wraps.
- `network-packet-classification/` -- C++ classifier and ruleset-analysis
  tools that consume ClassBench-ng's output. Must be on the `rule5D` branch
  for the classifier to be present (see Known issues).
- `pipeline/` -- Python pipeline that classifies the same ruleset/trace files
  directly, for iterating on classifier logic without a C++ rebuild.
- `data/` -- generated rulesets/traces land here, one subfolder per dataset
  (`data/<name>/ruleset.txt`, `data/<name>/trace.txt`). Gitignored -- these
  are regenerable and can get large (a 100k-rule trace is tens of MB).
- `scripts/` -- the actual generate/classify logic (`generate.sh`,
  `classify_cpp.sh`, `classify_py.sh`). Called through `make`/`docker
  compose` below; read them directly if you want to see exactly what runs.

## Setup

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).
Build the toolchain image once (rebuild only if `Dockerfile` changes):

```bash
docker compose build
# or: make build
```

This installs build-essential, cmake, Ruby + gems (`open4`, `ruby-ip`,
`docopt`, `ipaddress`), and python3 + numpy inside the image. The repo
itself is bind-mounted in at `/workspace` at run time, not baked into the
image -- editing source on the host takes effect immediately, and compiled
binaries (db_generator, trace_generator, the `m` classifier) persist on
disk across runs since they're written through the mount.

`network-packet-classification` needs to be on the `rule5D` branch (the
only branch with a working classifier):

```bash
git -C network-packet-classification checkout rule5D
```

## Commands

Every command below is `docker compose run --rm dev <script>`; `make`
targets are just short aliases for the same thing (skip `make` if you don't
have it -- e.g. on Windows without WSL/choco -- and run the `docker compose`
form directly).

### 1. Generate a ruleset + trace

```bash
make generate PROFILE=acl1 COUNT=1000
# same as: docker compose run --rm dev scripts/generate.sh acl1 1000
```

Writes `data/acl1_1000/ruleset.txt` and `data/acl1_1000/trace.txt`.

Full arg list: `generate.sh <profile> <rule_count> [name] [pareto_a] [pareto_b] [trace_scale]`

| arg | meaning |
|---|---|
| `profile` | Which ClassBench-ng seed to sample from (`classbench-packet-classification/parameter_files/`): `acl1`-`acl5` (router ACLs), `fw1`-`fw5` (firewall rulesets), `ipc1`-`ipc2` (core router "IP chain" classifiers). The number picks a different real-world-derived rule mix within that category, not a size. |
| `rule_count` | Target rule count. The actual output is usually somewhat lower -- ClassBench-ng drops redundant/duplicate rules during generation. |
| `name` | Subfolder under `data/` to write into. Default: `<profile>_<rule_count>`. |
| `pareto_a`, `pareto_b` | Shape the trace's locality of reference (how often the same rule gets hit repeatedly vs. uniformly at random). `a=1,b=0` = no locality, `a=1,b=0.0001` = low, `a=1,b=1` = high. Default `1`, `0.1`. |
| `trace_scale` | Trace size = `rule_count * trace_scale`. Default `10`. |

Each generated packet also carries a `filter_index`: the (0-indexed) line
number of the rule it was sampled from -- useful as an approximate ground
truth (see Notes below).

### 2. Classify with the C++ tool

```bash
make classify-cpp NAME=acl1_1000
# same as: docker compose run --rm dev scripts/classify_cpp.sh acl1_1000
```

Builds `network-packet-classification` with CMake if needed (incremental
after the first run) and runs `./m -r data/<name>/ruleset.txt -p
data/<name>/trace.txt -c linear`, which classifies every packet with
`LinearSearch` (brute-force, first match in priority order) and prints
match count + avg. lookup time. Optional second arg picks a different
registered classifier by name (see "Adding your own classifier" below):

```bash
make classify-cpp NAME=acl1_1000 CLASSIFIER=my_classifier
docker compose run --rm dev scripts/classify_cpp.sh acl1_1000 my_classifier
```

### 3. Classify with the Python pipeline (fast iteration)

```bash
make classify-py NAME=acl1_1000
# same as: docker compose run --rm dev scripts/classify_py.sh acl1_1000
```

Runs the same kind of classification in Python -- no C++ rebuild needed, so
this is the faster loop for trying out classifier logic changes. Optional
second arg picks the engine (`numpy`, default, or `python` for the plain
reference loop); anything else is forwarded to `pipeline/run_pipeline.py`:

```bash
make classify-py NAME=acl1_1000 ENGINE=python
docker compose run --rm dev scripts/classify_py.sh acl1_1000 --compare       # cross-check both engines agree
docker compose run --rm dev scripts/classify_py.sh acl1_1000 --limit 500     # quick smoke test
docker compose run --rm dev scripts/classify_py.sh acl1_1000 --out res.csv   # dump per-packet results
```

See `pipeline/README.md` for the pipeline's internals.

### One-shot

```bash
make test PROFILE=acl1 COUNT=1000   # generate + classify-cpp + classify-py
```

Equivalent without `make`, run in order:

```bash
docker compose run --rm dev scripts/generate.sh acl1 1000
docker compose run --rm dev scripts/classify_cpp.sh acl1_1000
docker compose run --rm dev scripts/classify_py.sh acl1_1000
```

### Shell / debugging

```bash
make shell   # drop into the container, repo at /workspace
# or: docker compose run --rm dev bash
```

## Demo

A full walkthrough of the pipeline on a small dataset -- generate, then
classify with both engines. Output below is abbreviated/illustrative: exact
rule/packet counts and timings vary run to run (ClassBench-ng's sampling
isn't deterministic, and timings depend on your machine).

**1. Build the image (once):**

```bash
docker compose build
# or: make build
```

**2. Generate a 1000-rule ACL ruleset + matching trace:**

```bash
make generate PROFILE=acl1 COUNT=1000
# or: docker compose run --rm dev scripts/generate.sh acl1 1000
```

```
Generating 1000-rule 'acl1' ruleset -> /workspace/data/acl1_1000/ruleset.txt
  -> 941 rules
Generating trace (pareto a=1 b=0.1, scale=10) -> /workspace/data/acl1_1000/trace.txt
  -> 9410 packets
Done: /workspace/data/acl1_1000/ruleset.txt, /workspace/data/acl1_1000/trace.txt
```

(On the very first run this also builds `db_generator`/`trace_generator`, so
expect a couple of extra "Building ... (first run only)" lines first.)

**3. Classify with the C++ `LinearSearch` classifier:**

```bash
make classify-cpp NAME=acl1_1000
# or: docker compose run --rm dev scripts/classify_cpp.sh acl1_1000
```

```
Read ruleset:  /workspace/data/acl1_1000/ruleset.txt
Read ruleset time(ns): 3218400
Read ruleset time(s): 0.0032184
Rread trace: /workspace/data/acl1_1000/trace.txt
Read trace time(ns): 8931200
Read trace time(s): 0.0089312
LinearSearch.packetCounter = 9410
classifier: linear
rule5V_num: 941
packet5V_num: 9410
search time avg (ns): 18342
search time avg (s): 1.8342e-05
```

Every packet "matches" here because of the `isMatch()` bug in Known issues
below (it only checks the source-IP prefix) -- don't read `packetCounter ==
packet5V_num` as a correctness signal.

**4. Classify with the Python pipeline instead (no C++ rebuild):**

```bash
make classify-py NAME=acl1_1000
# or: docker compose run --rm dev scripts/classify_py.sh acl1_1000
```

```
Loading ruleset: data/acl1_1000/ruleset.txt
Loading trace: data/acl1_1000/trace.txt
941 rules, 9410 packets

--- numpy ---
packets: 9410
matched: 9134 (97.07%)
unmatched: 276
agrees with generating rule (informational, overlaps make <100% expected): 8891/9410 (94.48%)
elapsed: 0.0842s  (111,758 packets/sec)
```

**5. Sanity-check both Python engines agree with each other:**

```bash
docker compose run --rm dev scripts/classify_py.sh acl1_1000 --compare
```

```
...
--- numpy ---
...

OK: all engines (python, numpy) agree.
```

## Known issues

- **`Rule5D::isMatch()` bug** (`network-packet-classification/lib/basis.hpp`,
  `rule5D` branch): it's written as an `if`/`else if` chain instead of
  independent checks, so in practice it only ever verifies the source-IP
  prefix and silently skips dest IP, both ports, and protocol for any rule
  with a non-wildcard source prefix. Fix this before trusting the C++
  classifier's output for anything beyond a smoke test.
- **`KsetSearch`/`TSearch` are unfinished** on this branch: both only
  implement `partition()` (building their internal structure); `search()`
  is declared in the header but never defined, so they can't classify
  packets yet. `main.cpp` only wires up `LinearSearch`.
- `analyDataset` (this repo's default branch before you checked out
  `rule5D`) doesn't have a classifier at all -- just ruleset-analysis tools
  (equivalent priority, coverage checking).

## Adding your own classifier

### C++

1. Add `network-packet-classification/classifiers/myClassifier.{hpp,cpp}`,
   matching `LinearSearch`'s shape -- a class with a
   `void search(std::vector<Rule5D>&, const std::vector<Packet5D>&)` method
   that, for each packet, walks `rule5V` and records/reports the matching
   rule (use `rule.isMatch(packet)`, or your own matching logic):

   ```cpp
   // classifiers/myClassifier.hpp
   #ifndef _CLASSIFIERS_MYCLASSIFIER_HPP_
   #define _CLASSIFIERS_MYCLASSIFIER_HPP_
   #include <vector>
   #include "../lib/basis.hpp"

   class MyClassifier {
    public:
     void search(std::vector<Rule5D>&, const std::vector<Packet5D>&);
   };
   #endif
   ```

   ```cpp
   // classifiers/myClassifier.cpp
   #include "myClassifier.hpp"
   #include <iostream>

   void MyClassifier::search(std::vector<Rule5D>& rule5V,
                              const std::vector<Packet5D>& packet5V) {
     size_t matched = 0;
     for (const auto& packet : packet5V) {
       for (auto& rule : rule5V) {  // isMatch() isn't const, needs non-const rule
         if (rule.isMatch(packet)) { ++matched; break; }
       }
     }
     std::cout << "MyClassifier matched: " << matched << "\n";
   }
   ```

   Note: `rule.isMatch(packet)` currently has the bug described above --
   fine for a scaffold/smoke test, but fix it (or write your own match
   logic) before trusting real results.

2. Register the `.cpp` in `classifiers/CMakeLists.txt`'s `target_sources`
   list, alongside `linearSearch.cpp`.

3. Wire it into `main.cpp`'s classifier dispatch (search for the `if
   (classifierName == "linear")` block) by adding an `else if`:

   ```cpp
   #include "myClassifier.hpp"   // add to the includes at the top
   ...
   } else if (classifierName == "my_classifier") {
     MyClassifier myClassifier;
     myClassifier.search(rule5V, packet5V);
   } else {
   ```

4. Run it -- `classify_cpp.sh`/`make classify-cpp` rebuild automatically:

   ```bash
   make classify-cpp NAME=acl1_1000 CLASSIFIER=my_classifier
   # same as: docker compose run --rm dev scripts/classify_cpp.sh acl1_1000 my_classifier
   ```

### Python

1. Add a function to `pipeline/classify.py` with the same signature as
   `linear_search`: `(rules: list[Rule], packets: list[Packet]) ->
   list[int]`, one matched priority (or `-1`) per packet, in the same order
   as `packets`.

   ```python
   def my_classifier(rules: list[Rule], packets: list[Packet]) -> list[int]:
       results = []
       for pkt in packets:
           match = next((r.priority for r in rules if r.matches(pkt)), -1)
           results.append(match)
       return results
   ```

2. Register it in `pipeline/run_pipeline.py`'s `ENGINES` dict:

   ```python
   ENGINES = {
       "python": linear_search,
       "numpy": linear_search_numpy,
       "my_classifier": my_classifier,   # add this
   }
   ```

3. Run it, and check it agrees with the existing engines before trusting it:

   ```bash
   make classify-py NAME=acl1_1000 ENGINE=my_classifier
   docker compose run --rm dev scripts/classify_py.sh acl1_1000 --compare   # add my_classifier to ENGINES first
   ```

   (`--compare` currently loops over every entry in `ENGINES`, so once
   yours is registered it's included automatically.)

## Notes

- Rule priority = line number in the ruleset file (0-indexed); the first
  line wins ties.
- A generated packet's `filter_index` (last column in the trace file) is
  the rule it was sampled from, not necessarily the first-priority match --
  ClassBench rulesets have legitimate overlapping rules, so a packet can
  correctly be classified by a *different*, higher-priority rule than the
  one that generated it. The pipeline's "agrees with generating rule" stat
  is informational (expect high-90s%), not a pass/fail correctness check.
