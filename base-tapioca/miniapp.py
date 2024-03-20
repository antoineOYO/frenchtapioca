from bottle import route, run, default_app, static_file, request, abort, response
import bottle
import sys
import json
import os
from pynif import NIFCollection
import logging
import settings
import numpy as np

from opentapioca.wikidatagraph import WikidataGraph
from opentapioca.languagemodel import BOWLanguageModel
from opentapioca.tagger import Tagger
from opentapioca.classifier import SimpleTagClassifier

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

tapioca_dir = os.path.dirname(__file__)

bow = BOWLanguageModel()
if settings.LANGUAGE_MODEL_PATH:
    bow.load(settings.LANGUAGE_MODEL_PATH)
graph = WikidataGraph()
if settings.PAGERANK_PATH:
    graph.load_pagerank(settings.PAGERANK_PATH)
tagger = None
classifier = None
if settings.SOLR_COLLECTION:
    tagger = Tagger(settings.SOLR_COLLECTION, bow, graph)
    classifier = SimpleTagClassifier(tagger)
    if settings.CLASSIFIER_PATH:
        classifier.load(settings.CLASSIFIER_PATH)


text = 'Villeurbanne, Lyon et Miribel sont 3 agglomérations lyonnaises.'
if not classifier:
    mentions = tagger.tag_and_rank(text)
else:
    mentions = classifier.create_mentions(text)
    classifier.classify_mentions(mentions)


for m in mentions:
    besttag = sorted(m.json()['tags'], key=lambda x: x['score'])[-1]
    print(text[m.start:m.end],
          ' tagged as ',
          besttag['label'],
          besttag['id'],
          ' with log likelihood ', 
          # arrondi à 10-2 :
          np.round(m.json()['log_likelihood'], 3)
    )
    
