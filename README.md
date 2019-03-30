# MetaMap-REST-API

## Introduction

This is a REST API that integrates MetaMap. Internally, we created a MetaMap Python helper called MetaMaPY. On top of the MetaMaPY, we created a REST API using Flask. This app should be served with uWSGI for deployment, although we can run locally without it. Sample config files has been added for both local deployment and server deployment.

### MetaMap
MetaMap is a NLP (Natural Language Processing) developed by NLM (National Library of Medicine) at NIH, for info can be found on this site [https://metamap.nlm.nih.gov](https://metamap.nlm.nih.gov). MetaMap is used for mapping biomedical text to the UMLS Metathesaurus or, equivalently, to discover Metathesaurus concepts referred to in text. In our case, we use it to map text into UMLS Metathesaurus, more specifically, only HPO (Human Phenotype Ontology) terms.

### MetaMaPY
Since MetaMap is a Java based command line tool. We wrapped it with Python and integrate with modern web technologies to build a REST API. To improve its performance, we used parallel programming to allow MetaMap running on several cores simultaneously so that we can get the most out of the computer power of the server. Additionally, we implemented a MRU (Most Recently Used) cache that stores the most recently used queries to boost the response time.

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

### `/metamap/keyword/<string:keyword>`

Querying with only a keyword. The API will try to search OMIM and PubMed for matching articles and run them through MetaMap. 

We recommend that the keyword be an RSID, since we only query OMIM with RSID. But you may use it with any keywords, and we will try to search that keyword on PubMed.

You may interact with the `/metamap/keyword/<string:keyword>` endpoint using **POST** method with the following header and body:

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

Notice that the header and body are optional, and must be used together if chosen. This endpoint holds a query cache that stores previous results and will respond immediately if the current keyword hits the cache.

This endpoint uses cache by default. You may pass in the `use_cache` field with `false` in the request body and opt-out using cache.
 