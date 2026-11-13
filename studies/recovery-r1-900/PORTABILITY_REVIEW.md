# Portable reproduction: changes requiring review

The original drivers remain unchanged and host-dependent. A new, separately
authorized `portable_replay.py` wrapper addresses path/loading for the fixed
case75 replay, without importing or editing those drivers. Its first-use
protocol and results are linked from the study README. The obstacles and
original proposal below explain which source behavior it avoids.

## Exact obstacles

1. `frozen/r1_recovery_runner.py` sets `REPO` to the original Windows checkout,
   inserts that path into `sys.path`, and imports its `Analysis` modules. Its
   `models()` reads physical models from that checkout. Merely importing the
   module calls `load_tensor_kernel()`, which writes a kernel and diff beside
   the runner.
2. `frozen/r1_bounded_v2.py` imports that runner, then calls `kernel()` at module
   scope. This writes another kernel and diff. Its `rotor_centres()` dereferences
   each model's original `physical_model_path`.
3. The campaign branch builds its freeze record with host paths, and writes the
   campaign directory beside the source. A copied `--campaign` invocation could
   regenerate cohort/metadata or collide with retained output paths.
4. `frozen/audit_completed_v2.py` expects the original campaign folder beside its
   source and checks original absolute paths from the freeze record. It writes
   an audit, plots and a LaTeX table. Moving that file alone is not a read-only
   audit or portable reduction.
5. Original frozen hashes identify exact Windows checkout bytes. Git text blobs
   may use LF line endings. The copied evidence is byte-exact and protected by
   study-local `-text` attributes; neither representation may be substituted
   silently when checking a registered hash.
6. The original freeze does not supply a complete historical Python/dependency
   environment lock. The repository's current requirements do not prove which
   environment produced the archived outcomes. Bitwise result reproduction has
   not been demonstrated on another host.

## Original adaptation proposal

1. Introduce explicit immutable input-root and fresh output-root parameters.
   Resolve baseline source and CAD inputs through an approved path map instead
   of the original `REPO` constant. Retain the original files and paths in the
   provenance record.
2. Remove kernel/diff writes from module import. Load the saved executed kernels
   for inspection/rerun, or generate derivatives only in the fresh output root
   after exact source-match guards. Avoid changing arithmetic, integration,
   allocation, gains, cohort ordering, seeds, model inputs or acceptance limits.
3. Separate cohort loading from cohort generation. An approved reproduction
   should consume the copied frozen cohort and original plant records; it must
   never replace those records because a new sampler run looks equivalent.
4. Resolve original freeze paths to copied files through `source-map.json`,
   retaining each exact registered hash. Stop on any unrecognized path or
   content difference. Do not normalize arbitrary content or rewrite the old
   manifest to make a relocated run pass.
5. Separate inspection from post-processing that writes. Give audit/plot/table
   outputs their own fresh directory. The raw saved metrics and their reduction
   can be inspected without re-running physics; a trajectory-level independent
   reduction needs newly retained trajectories under an approved protocol.
6. Record the actual environment for a future reproduction. Compare a small
   reviewed preservation case first under unchanged acceptance gates. Any new
   discrepancy is a finding to report, not permission to retune the model or
   acceptance limits.

The wrapper implements the relevant path/loading separation for the fixed
selected cases only. It does not port the original campaign/audit drivers,
regenerate original outputs or prove cross-host bitwise reproduction. Source
review, broader reproduction and physical qualification remain separate work.
