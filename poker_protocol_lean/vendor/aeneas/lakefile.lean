import Lake
open Lake DSL
-- Vendored from Aeneas release `nightly-2026.10.07-aa66752`
-- (backends/lean), trimmed to the Aeneas + AeneasMeta libraries.
-- mathlib repinned from v4.31.0 to v4.32.0 to match this project.

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.32.0"

package «aeneas» where
  preferReleaseBuild := false

@[default_target]
lean_lib «Aeneas» {}

@[default_target]
lean_lib «AeneasMeta» where
  precompileModules := false
