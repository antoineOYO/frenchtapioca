import json
import requests
import logging
import re
from math import log

from .languagemodel import BOWLanguageModel
from .wikidatagraph import WikidataGraph
from .tag import Tag
from .mention import Mention

# solr_collection = 'wd_multilingual'
logger = logging.getLogger(__name__)

class Tagger(object):
    """
    The tagger indexes a Wikidata dump in Solr
    input: solr_collection, bow, graph !
    and uses it to detect efficiently mentions of Wikidata
    items in text.
    """

    def __init__(self, solr_collection, bow, graph):
        """
        Creates a tagger from:
        - a solr collection name, which has been adequately initialized with a compatible index and filled with documents
        - a bag of words language model, adequately trained, which will be used to evaluate the likelihood of phrases
        - a wikidata graph, adequately loaded, which will be used to compute the page rank and the edges between items
        """
        self.bow = bow
        self.graph = graph
        self.solr_endpoint = 'http://localhost:8983/solr/{}/tag'.format(solr_collection)

        #tokens or numbers up to 4 digits (years) :
        self.prune_re = re.compile(r'^(\w\w?|[\d ]{,4})$')

        self.max_length = 10000

        self.rank_shift = self.graph.get_pagerank('Q9999999999999999999999999999999999999999')

    def tag_and_rank(self, phrase, prune=True):
        """
        Given some text, use the solr index to retrieve candidate items mentioned in the text.
        :param prune: if True, ignores lowercase mentions shorter than 3 characters
        """
        # Tag
        phrase = phrase[:self.max_length]
        logger.debug('Tagging text with solr (length {})'.format(len(phrase)))
        r = requests.post(self.solr_endpoint,
            params={'overlaps':'NO_SUB',
             'tagsLimit':500,
             'fl':'id,label,aliases,extra_aliases,desc,nb_statements,nb_sitelinks,edges,types',
             'wt':'json',
             'indent':'off',
            },
            headers ={'Content-Type':'text/plain'},
            data=phrase.encode('utf-8'))
        r.raise_for_status()
        logger.debug('Tagging succeeded')
        resp = r.json()

        # Enhance mentions with page rank and edge similarity
        mentions_json = [
            self._dictify(mention)
            for mention in resp.get('tags', [])
        ]
        docs = {
            doc['id']:doc
            for doc in resp.get('response', {}).get('docs', [])
        }

        mentions = [
            self._create_mention(phrase, mention, docs, mentions_json)
            for mention in mentions_json
        ]

        pruned_mentions = [
            mention
            for mention in mentions
            if not self.prune_phrase(mention.phrase)
        ]

        return pruned_mentions

    def prune_phrase(self, phrase):
        """
        Should this phrase be pruned? It happens when
        it is shorter than 3 characters and appears in lowercase in the text,
        or only consists of digits.

        This is mostly introduced to remove matches of Wikidata items about characters,
        or to prevent short words such as "of" or "in" to match with initials "OF", "IN",
        as well as sport scores, postcodes, and so on.
        """
        return self.prune_re.match(phrase) is not None and phrase.lower() == phrase

    def _create_mention(self, phrase, mention, docs, mentions):
        """
        Adds more info to the mentions returned from Solr, to prepare
        them for ranking by the classifier.

        :param phrase: the original document
        :param mention: the JSON mention to enhance with scores
        :param docs: dictionary from qid to item
        :param mentions: the list of all mentions in the document
        :returns: the enhanced mention, as a Mention object
        """
        start = mention['startOffset']
        end = mention['endOffset']
        surface = phrase[start:end]
        surface_score = self.bow.log_likelihood(surface)
        ranked_tags = []
        for qid in mention['ids']:
            item = dict(docs[qid].items())

            #log(pagerank) = log(pagerank) - log(rank_shift) with log(rank_shift) approx 23
            item['rank'] = log(self.graph.get_pagerank(qid)) - log(self.rank_shift)
            
            item['label'] = item['label'][0] if item.get('label') else None
            ranked_tags.append(Tag(**item))

        return Mention(
            phrase=surface,
            start=start,
            end=end,
            log_likelihood=-surface_score,
            tags=sorted(ranked_tags, key=lambda tag: -tag.rank)[:10],
        )

    def _dictify(self, lst):
        """
        Converts a list of [key1,val1,key2,val2,...] to a dict
        """
        return {
            lst[2*k]: lst[2*k+1]
            for k in range(len(lst)//2)
        }


if __name__ == '__main__':
    import sys
    fname = sys.argv[1]
    print('Loading '+fname)
    bow = BOWLanguageModel()
    bow.load(fname)
    print('Loading '+sys.argv[2])
    graph = WikidataGraph()
    graph.load_pagerank(sys.argv[2])
    tagger = Tagger(bow, graph)

    while True:
        phrase = input('>>> ')
        tags = tagger.tag_and_rank(phrase)
        for mention in tags:
            for tag in mention.get('tags', []):
                if 'edges' in tag:
                    del tag['edges']
                if 'aliases' in tag:
                    del tag['aliases']
        print(json.dumps(tags, indent=2, sort_keys=True))

