- Models and indexes:
  - add Item.lang
  - the triggers should sync the index tables but not both langs, only the one with the 
      correct lang: use the WHEN condition https://sqlite.org/lang_createtrigger.html
  - write proper tests for models

- output schema in CLI views with console.print(), search "TODO use output schema?"
- `admin-db-run-migrations` CLI

- Read all this: https://sqlite.org/fts5.html

- Main repo's README.md,
  main project's one,
  the one in snowball dir

- New experiment: sqlite-full-text-search-aws-exp
  - Lambda + SQLite arch on AWS:
  https://github.com/puntonim/patatrack-monorepo/blob/main/projects/contabel/docs/img/architecture-draw.io.svg


