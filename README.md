# MetaMap-REST-API

## Introduction

This is a REST API that integrates MetaMap. Internally, we created a MetaMap Python helper called MetaMaPY. On top of the MetaMaPY, we created a REST API using Flask. This app should be served with uWSGI for deployment, although we can run locally without it. Sample config files has been added for both local deployment and server deployment.

### MetaMap

MetaMap is a NLP (Natural Language Processing) developed by NLM (National Library of Medicine) at NIH, for info can be found on this site [https://metamap.nlm.nih.gov](https://metamap.nlm.nih.gov). MetaMap is used for mapping biomedical text to the UMLS Metathesaurus or, equivalently, to discover Metathesaurus concepts referred to in text. In our case, we use it to map text into UMLS Metathesaurus, more specifically, only HPO (Human Phenotype Ontology) terms.

### MetaMaPY

Since MetaMap is a command line tool. We wrapped it with Python and Flask to build a REST API. To improve its performance, we used parallel programming to allow MetaMap running on several cores simultaneously so that we can get the most out of the computer power of the server. Additionally, we implemented a MRU (Most Recently Used) cache that stores the most recently used queries to boost the response time.

One can specify the number of paralleling processes using environment variable `MAX_PROCESSES`. Usually using the number of cores in CPU would give you best performance. If the CPU has hyperthreading feature, 2 times of cores may result in the best performance.
 
## Usage

For now, the API contains two endpoints:

### `/metamap/articles`

You may interact with the `/metamap/articles` endpoint using **POST** method with the following header and body:

#### header

```
content-type: application/json
```

#### body

```

{
    "articles": [  // a list of articles
        {
            "source": <source name of the article, e.g pubmed>,
            "id": <id within the source, e.g. PMID>,
            "text": <the text to process>
        },
        ...
    ]
}
```

### `/metamap/term/<string:term>`

Querying with only a search term. The API will try to search OMIM and PubMed for matching articles and run them through MetaMap. 

We recommend that the term be an RSID, since we only query OMIM with RSID. But you may use it with any term, and we will try to search that keyword on PubMed.

You may interact with the `/metamap/term/<string:term>` endpoint using **POST** method with the following header and body:

#### response

The response will be a json string with field `terms` containing a list of extracted terms. Each extracted term contains 5 fields: 

- `term`: extracted term.
- `category`: term category.
- `count`: occurrence.
- `sources`: source from where the term has been extracted.
- `CUI`: MetaMap UMLS id.

The `source` sub-field should contain the name of the source, mapped with a list of UIDs in that source. For example:

```
"sources": {
    "pubmed": [
        "30389547"
    ]
}
```

means the term comes from a ***PubMed*** article with PMID 30389547.
 
Sample response:

```json
{
    "terms": [
        {
            "term": "Multiple Sclerosis",
            "category": "Disease or Syndrome",
            "count": 11,
            "sources": {
                "pubmed": [
                    "30389547"
                ]
            },
            "CUI": "C0026769"
        },
        {
            "term": "MS gene",
            "category": "Gene or Genome",
            "count": 11,
            "sources": {
                "pubmed": [
                    "30389547"
                ]
            },
            "CUI": "C1417325"
        }
    ]
}
```

#### header

```
content-type: application/json
```

#### body

```

{
    "use_cache": <true or false>
}
```

Notice that the header and body are optional, and must be used together if chosen. This endpoint holds a query cache that stores previous results and will respond immediately if the current term hits the cache.

This endpoint uses cache by default. You may pass in the `use_cache` field with `false` in the request body and opt-out using cache.
 
#### response

The response body is similar with that of `/metamap/articles` endpoint. Except that there an additional `key` field where key is the term used for the query. This key is used in the cache and future queries with the same key may get immediate response from the cache.

Sample response:

```
{
    "key": "rs333",
    "terms": [...]
}
