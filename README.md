# movie-search-engine

## Motivation

A more effective way to approach this problem is by getting a semantic vector for all of the words contained in a document, that is, a language-specific representation of such words. So, when you search for a word like "jump", you will match all instances of the word and its tenses, even if you searched for "jumped" or "jumping". Additionally, you won't be searching the full document itself (which is slow), but the vector (which is fast).

Search is one of the most important features while building an application. It leads to an increase in the popularity of various search engines like Elastic Search, Solr, etc. However, all of them require a different server to be set up and data sync processes to be implemented. Would it not be better to have a solution that could minimize overheads and allow us to focus on the main objective, which is Search? Yes, and that's where the Postgres Full-Text Search comes into the picture. It searches for the data right where it is stored in your tables. There is no need to set up a different server.

## Indexes

In choosing which index type to use, GiST or GIN, consider these performance differences:

- GIN index lookups are about three times faster than GiST
- GIN indexes take about three times longer to build than GiST
- GIN indexes are moderately slower to update than GiST indexes, but about 10 times slower if fast-update support was disabled (see Section 58.4.1 for details)
- GIN indexes are two-to-three times larger than GiST indexes

As a rule of thumb, GIN indexes are best for static data because lookups are faster. For dynamic data, GiST indexes are faster to update. Specifically, GiST indexes are very good for dynamic data and fast if the number of unique words (lexemes) is under 100,000, while GIN indexes will handle 100,000+ lexemes better but are slower to update.
