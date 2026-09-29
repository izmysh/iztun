# Contributing

1. Fork this GUI repository, not the upstream protocol repositories.
2. Clone your fork with `--recurse-submodules`.
3. Create a topic branch from `main`.
4. Keep VPN profiles, keys, addresses and customer data out of commits.
5. Run `make test` and the optional GTK checks in README before opening a pull request.
6. Describe the target distribution, architecture, desktop session and the
   AmneziaWG profile generation when reporting a compatibility problem.

Changes to `upstream/amneziawg-go` or `upstream/amneziawg-tools` belong in the
respective upstream project. This repository should normally only update the
pinned revision after an upstream release has been tested. The original developer
checkout uses submodules; a checkout created from the complete release archive
vendors their sources. Keep `UPSTREAM_VERSIONS` and licenses accurate in either case.
