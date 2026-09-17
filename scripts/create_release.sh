#!/usr/bin/env bash
# Promote the current main to a GitHub Release, which is what publishes to PyPI.
#
#   scripts/create_release.sh            # version taken from pyproject.toml
#   scripts/create_release.sh 2.6.0      # version given explicitly
#   DRY_RUN=1 scripts/create_release.sh  # run every check, create nothing
#
# The release tag targets main, so the workflow that runs is the one on main.
# Tagging an older commit would run that commit's workflow, which may not have
# the `release` trigger at all.
set -euo pipefail

cd "$(dirname "$0")/.."

fail() { printf '\n\033[31mERRO:\033[0m %s\n' "$1" >&2; exit 1; }
step() { printf '\033[36m==>\033[0m %s\n' "$1"; }

pyproject_version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
[[ -n "$pyproject_version" ]] || fail "não consegui ler a versão do pyproject.toml"

version="${1:-$pyproject_version}"
version="${version#v}"
tag="v${version}"

step "Versão: ${version} (tag ${tag})"

# The publish job refuses a tag that disagrees with pyproject.toml, so catch it here.
if [[ "$version" != "$pyproject_version" ]]; then
    fail "pyproject.toml está em ${pyproject_version}, não em ${version}.
     Faça o bump e o commit antes de criar o release."
fi

step "Conferindo o estado do repositório"
branch=$(git rev-parse --abbrev-ref HEAD)
[[ "$branch" == "main" ]] || fail "você está em '${branch}'; o release sai da main."

[[ -z "$(git status --porcelain)" ]] || fail "há alterações não commitadas. Commite ou descarte antes."

git fetch -q origin main
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
    fail "main local e origin/main estão diferentes. Dê push (ou pull) antes."
fi

if git ls-remote --exit-code --tags origin "refs/tags/${tag}" >/dev/null 2>&1; then
    fail "a tag ${tag} já existe no remoto."
fi

step "Extraindo as notas de docs/CHANGELOG.md"
notes_file=$(mktemp -t "release-${version}")
trap 'rm -f "$notes_file"' EXIT
VERSION="$version" python3 - > "$notes_file" <<'PY'
import os
import pathlib
import re
import sys

version = re.escape(os.environ["VERSION"])
text = pathlib.Path("docs/CHANGELOG.md").read_text(encoding="utf-8")
match = re.search(rf"## \[{version}\][^\n]*\n(.*?)(?=\n## \[|\Z)", text, re.S)
if not match or not match.group(1).strip():
    sys.exit(f"docs/CHANGELOG.md não tem uma seção para {os.environ['VERSION']}")
print(match.group(1).strip())
PY

printf '\n\033[2m--- notas do release ---\033[0m\n'
cat "$notes_file"
printf '\033[2m------------------------\033[0m\n\n'

if [[ -n "${DRY_RUN:-}" ]]; then
    step "DRY_RUN — nada foi criado. Tudo pronto para ${tag}."
    exit 0
fi

read -r -p "Criar o release ${tag} a partir da main? [s/N] " answer
[[ "$answer" =~ ^[sSyY]$ ]] || fail "cancelado."

step "Criando o release"
gh release create "$tag" --target main --title "$tag" --notes-file "$notes_file"

step "Acompanhando o workflow (Ctrl+C para sair; o run continua)"
sleep 5
run_id=$(gh run list --event release --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch "$run_id" --exit-status
