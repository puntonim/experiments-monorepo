
# ** SQLITE FULL-TEXT SEARCH EXPERIMENT **



Index tables **with content** ot with **external-content**
==========================================================

Docs on external-content: https://sqlite.org/fts5.html#external_content_tables

Index tables can be **with content** or with **external-content** (or contentless).
 - Index tables with content duplicate the content (all the indexed cols) of the
    original table (by creating a new extra table with the original content).
 - While index tables with external-content do not, but instead when the search returns
    the original content, they transparently make a join query with the original table.

Notice that the SQL queries done on index tables **with content**/with **external-content**
 are exactly the same. But under the hood the search queries on **external-content** 
 index tables are more expensive (because there are transparent joins).

=> So the **external-content** saves disk space at the cost of a bit slower search queries.

This is the internal (virtual) tables created in both cases:
![alt text](docs/img/Index tables with external-content.png)

SQL queries **with content**
----------------------------
```py
# Insert:
('INSERT INTO "itemftsindexita" ("rowid", "title", "notes") VALUES (?, ?, ?)', [1, 'My first title', 'My first note'])
# Select:
('SELECT "t1"."rowid", "t1"."title", "t1"."notes" FROM "itemftsindexita" AS "t1"', [])
# Search:
('SELECT "t1"."rowid", bm25("itemftsindexita") AS "score", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "title_h", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "notes_h" FROM "itemftsindexita" AS "t1" WHERE ("itemftsindexita" MATCH ?) ORDER BY bm25("itemftsindexita") DESC', [0, '<<', '>>', '...', 64, 1, '<<', '>>', '...', 64, 'dente'])
```

SQL queries with **external-content**
-------------------------------------
Queries are exactly the same as above.
What changes is that the search query, in this case, executes some joins under the hood.
```py
# Insert:
('INSERT INTO "itemftsindexita" ("rowid", "title", "notes") VALUES (?, ?, ?)', [1, 'Il primo titolo ...', 'La prima nota ...'])
# Select:
('SELECT "t1"."rowid", "t1"."title", "t1"."notes" FROM "itemftsindexita" AS "t1"', [])
# Search:
('SELECT "t1"."rowid", bm25("itemftsindexita") AS "score", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "title_h", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "notes_h" FROM "itemftsindexita" AS "t1" WHERE ("itemftsindexita" MATCH ?) ORDER BY bm25("itemftsindexita") DESC', [0, '<<', '>>', '...', 64, 1, '<<', '>>', '...', 64, 'dente'])
```



