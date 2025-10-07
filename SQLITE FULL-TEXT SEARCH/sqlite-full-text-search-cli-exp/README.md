TODO


With content
------------
```py
# Insert:
('INSERT INTO "itemftsindexita" ("rowid", "title", "notes") VALUES (?, ?, ?)', [1, 'My first title', 'My first note'])
# Select:
('SELECT "t1"."rowid", "t1"."title", "t1"."notes" FROM "itemftsindexita" AS "t1"', [])
# Search:
('SELECT "t1"."rowid", bm25("itemftsindexita") AS "score", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "title_h", snippet("itemftsindexita", ?, ?, ?, ?, ?) AS "notes_h" FROM "itemftsindexita" AS "t1" WHERE ("itemftsindexita" MATCH ?) ORDER BY bm25("itemftsindexita") DESC', [0, '<<', '>>', '...', 64, 1, '<<', '>>', '...', 64, 'dente'])
```

With extern-content
-------------------

