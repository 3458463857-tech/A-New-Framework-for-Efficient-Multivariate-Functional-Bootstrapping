# Source this helper before any build, execution, or log write.
# Explicit existing nonempty directories are rejected; no results are deleted.
new_output_directory() {
  local prefix="$1"
  local requested="${2:-}"
  if [[ -n "$requested" ]]; then
    OUT="$requested"
  else
    OUT="$ROOT/results/${prefix}_$(date -u +%Y%m%dT%H%M%S)_$$"
  fi
  if [[ -e "$OUT" ]]; then
    if [[ ! -d "$OUT" ]] || [[ -n "$(find "$OUT" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
      printf 'Refusing to overwrite nonempty output path: %s\n' "$OUT" >&2
      return 2
    fi
  fi
  mkdir -p "$OUT"
  OUT="$(cd "$OUT" && pwd)"
}
