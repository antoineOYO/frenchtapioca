
# The name of the Solr collection where Wikidata is indexed
SOLR_COLLECTION = 'englishtapioca'

# The path to the language model, trained with "tapioca train-bow"
LANGUAGE_MODEL_PATH='data/all-english.bow.pkl'
# The path to the pagerank Numpy vector, computed with "tapioca compute-pagerank"
PAGERANK_PATH='data/wikidata/wikidata-graph.pgrank.npy'
# The path to the trained classifier, obtained from "tapioca train-classifier"
CLASSIFIER_PATH='data/latest_classifier.pkl'