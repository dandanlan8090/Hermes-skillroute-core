# Obsidian Tool Guide

Use this reference for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable (e.g. from `${HERMES_HOME:-~/.hermes}/.env`). If unset, fall back to `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

## Read a note

Use `read_file` with the resolved absolute path to the note.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Use `pattern: "*.md"` to list all markdown notes.

## Search

Use `search_files` for both filename and content searches. For note contents, use `file_glob: "*.md"` to restrict to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content.

## Append to a note

- Read the target note with `read_file`.
- Use `patch` for an anchored append (e.g. adding a section after an existing heading).
- Use `write_file` when rewriting the whole note is clearer.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
