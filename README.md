# movie-search-engine

Exploration of PostgreSQL's built-in full text search capabilities to build a movie search engine on top of a dummy movies database.

## Motivation

The usual `LIKE`, `ILIKE` and `~` operators do not really fit the requirements of real world human search queries. They can match literal substrings in an arbitrary document, but they were not designed to take into account all instances, cases or tenses of any given word. To meet the needs of real world search patterns we need more sophisticated techniques that use natural language processing to ignore stop words (e.g. the, and), ignore casing, remove synonyms and employ stemming algorithms to obtain the resulting lexeme which is computed for every word of the document and represented as a vector for faster searching.

It is also very important to note that even though you can create an index on the column you're searching, only queries like `LIKE 'foo%'` (with a wildcard at the end) will actually use the index. On the other hand queries like `LIKE '%foo%'` or `LIKE '%foo'` (with a wildcard at the start) never use the index because of how the search algorithm works in a typical B-Tree index, and instead just do a full table scan. In short, in addition to not having been designed for human search queries, the `LIKE` operator and friends don't really scale to large databases because any indexes you may have created are inherently not used for most search queries.

The need for proper full text search leads to an increase in the popularity of various search engines like Elastic Search, Solr, etc. But all of them require a different server to be set up and data sync processes to be implemented. However PostgreSQL has built-in full text search support, allowing you to run sophisticated search queries right in your database where the rest of your data is without needing to set up a different server.

In this experiment (a project for an Advanced Databases class) we will explore the built in full text search capabilities of PostgreSQL on a dummy movies database.

## Schema

The database schema used for this experiment is described in `movies.sql` and can be executed idempotently:

```
$ psql movie-search-engine
movie-search-engine=# \i movies.sql
```

## tsvector

The document `The big blue elephant jumped over the crippled blue dolphin.` can be converted to a `tsvector` using `to_tsvector('The big blue elephant jumped over the crippled blue dolphin.')` which results in a vector data structure like this where each lexeme is assigned its position in the original document:

```
'big':2 'blue':3,9 'crippl':8 'dolphin':10 'eleph':4 'jump':5
```

Notice how PostgreSQL has stemmed and reduced the words to match all possible variants. The lexeme "crippl", for example, matches "cripple", "crippled", "crippling", "cripples", etc. which would be impossible using the classic `LIKE` operator.

It is also possible to assign weights (A, B, C, D - from highest to lowest priority) to part of your document. For example, if the original document consisted of a title, body and footer, you could give more importance to the title when building the `tsvector`, which full text search can then leverage to rank search results differently and more usefully.

```
setweight(to_tsvector('the big blue elephant'), 'A') ||
setweight(to_tsvector('jumped over the'), 'B') ||
setweight(to_tsvector('crippled blue dolphin.'), 'C')
```

## tsquery

To query a `tsvector` you can convert your query string into a `tsquery` data structure and then search using the `@@` operator:

```
SELECT phrase FROM phrases WHERE to_tsvector(phrase) @@ to_tsquery('english', 'elephants');
```

But, of course, for performance you should store the `tsvector` in the table itself rather than computing it at runtime for every row. You can setup a trigger to keep the `tsvector` field always updated and then you just refer to this new (let's call it `tsv`) field normally.

```
SELECT phrase FROM phrases WHERE tsv @@ to_tsquery('english', 'elephants');
```

You can build more complex queries with the familiar `&`, `|` and `!` binary operators to exactly or partially match phrases or even exclude them.

## Indexes

In choosing which index type to use, GiST or GIN, consider these performance differences:

- GIN index lookups are about three times faster than GiST
- GIN indexes take about three times longer to build than GiST
- GIN indexes are moderately slower to update than GiST indexes, but about 10 times slower if fast-update support was disabled
- GIN indexes are two-to-three times larger than GiST indexes

As a rule of thumb, GIN indexes are best for static data because lookups are faster. For dynamic data, GiST indexes are faster to update. Specifically, GiST indexes are very good for dynamic data and fast if the number of unique words (lexemes) is under 100,000, while GIN indexes will handle 100,000+ lexemes better but are slower to update.

With that in mind, a GIN index was created on the `tsv` column to speed up full text searches:

```
CREATE INDEX tsv_index ON movies USING gin(tsv);
```

## Rank Results

It is useful to order search results by rank, which we can accomplish using `ts_rank` (highly configurable but for simplicity we'll stick to default settings) but when used in a select statement `ts_rank` will rank all rows returned from a query, most of which will probably have a ranking of 0, so it's faster to do a search without `ts_rank` in a limited subquery and then `ts_rank` said subquery results so that `ts_rank` is only applied to a limited subset of the search results.

## Highlight Results

The same reasoning applies to the `ts_headline` function which only really needs to be applied to the top ranked results, not prematurely to every search result.
