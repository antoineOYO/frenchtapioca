import pickle

import re
from unidecode import unidecode
from collections import defaultdict
from math import log
from opentapioca.readers.dumpreader import WikidataDumpReader
import json
from opentapioca.wditem import WikidataItemDocument

separator_re = re.compile(r'[,\-_/:;!?)]? [,\-_/:;!?(]?')

def tokenize(phrase):
    """
    Split a text into lists of words
    """
    words = [
        unidecode(word.strip())
        for word in separator_re.split(' '+phrase+' ')
    ]
    return [w for w in words if w]

class BOWLanguageModel(object):
    def __init__(self):
        ################ Laplace Smoothing ################
        # https://en.wikipedia.org/wiki/Additive_smoothing
        # P_unit_laplace(w) = (count(w) + 1) / (N + V [+1])
        # with  N = size of the corpus to be tokenized i.e. number of samples
        #       V = size of the vocabulary
        # Now with smoothing alpha factor:
        # P_smoothed_laplace(w) = (count(w) + alpha) / (N + alpha * V)
        # in this fraction, count(w) + alpha  does not depend on the step of the processing
        # so the denominator can be computed once and for all at the end, for example
        # we load the ML with the method load()
        self.total_count = 0
        self.word_count = defaultdict(int)
        self.smoothing = 1
        self.log_quotient = None
        self.threshold = 2

    def ingest(self, words):
        """
        Ingests a sequence of words in the language model
        """
        for word in words:
            self.word_count[word] += 1
        self.total_count += len(words)

    def ingest_phrases(self, phrases):
        """
        Given a list of strings (phrases), deduplicate all
        their words and ingest them.
        """
        word_set = set()
        for phrase in phrases:
            word_set |= set(tokenize(phrase))
        self.ingest(word_set)

    def log_likelihood(self, phrase):
        """
        Returns the log-likelihood of the phrase
        """
        words = tokenize(phrase)
        return sum(self._word_log_likelihood(word) for word in words)

    def _word_log_likelihood(self, word):
        """
        The log-likelihood for for EACH NEW TOKEN WE MEET IN THE CORPUS
        --> HEART OF THE LANGUAGE MODEL
        --> UPDATED UNTIL THE LAST WORD IS PROCESSED
        """
        if self.log_quotient is None:
            self._update_log_quotient()
        return log(float(self.smoothing + self.word_count[word])) - self.log_quotient

    def _update_log_quotient(self):
        """
        Updates the precomputed quotient
        """
        self.log_quotient = log(self.smoothing*(1+len(self.word_count))+self.total_count)

    def load(self, filename):
        """
        Loads a pre-trained language model
        RECOMPUTES THE LOG QUOTIENT THROUGH _update_log_quotient()
        """
        with open(filename, 'rb') as f:
            dct = pickle.load(f)
            self.total_count = dct['total_count']
            self.word_count = defaultdict(int, dct['word_count'])
            self._update_log_quotient()

    def save(self, filename):
        """
        Saves the language model to a file
        """
        print('saving language model')
        with open(filename, 'wb') as f:
            pickle.dump(
                {'total_count':self.total_count,
                 'word_count':[ (w,c) for w,c in self.word_count.items()
                                if c >= self.threshold ]},
                f)


    @classmethod
    def train_from_dump(cls, filename):
        """
        Trains a bag of words language model from either a .txt
        file (in which case it is read as plain text) or a .json.bz2
        file (in which case it is read as a wikidata dump).
        """
        bow = BOWLanguageModel()
        if filename.endswith('.txt'):
            with open(filename, 'r') as f:
                for line in f:
                    bow.ingest_phrases([line.strip()])

        elif filename.endswith('.json.bz2'):
            with WikidataDumpReader(filename) as reader:
                for idx, item in enumerate(reader):
                    if idx % 10== 0:
                    #if idx % 10000 == 0:
                         print('\rTeaching step : ' + str(idx), end='', flush=True)
                         
                    labels = item.get('labels', {})
                    frlabel = labels.get('fr', {}).get('value')
                    #frdesc = item.get('descriptions', {}).get('fr', {}).get('value')    
                    
                    if frlabel:

                        # Fetch aliases

                        fraliases = [ 
                            alias['value'] 
                            for alias in item.get('aliases', {}).get('fr', [])
                        ] 

                        
                        bow.ingest_phrases(fraliases + [frlabel])

                        # if bow.word_count[frlabel] > 1:
                        #      print('duplicate label: ' + frlabel)
                        #      print(bow.word_count[frlabel]) 
                        
                        # if bow.word_count['Nord'] > 5:
                        #     print('duplicate label: ' + frlabel)
                        #     print(bow.word_count[frlabel])
                        #     print('stopping')
                        #     break
        else:
            raise ValueError('invalid filename provided (must end in .txt or .json.bz2)')

        print('\nDone teaching language model with {} documents'.format(idx+1))
        return bow


    @classmethod
    def train_from_json(cls, filename, language):
        """
        Trains a bag of words language model from either a .txt
        file (in which case it is read as plain text) or a .json.bz2
        file (in which case it is read as a wikidata dump).
        """
        bow = BOWLanguageModel()
        
        with open(filename, 'r') as f:
            item = WikidataItemDocument(json.load(f))
            preferred_label = item.get_default_label(language)
            aliases = item.get_aliases(language)
            bow.ingest_phrases([preferred_label] + aliases)
            #print(preferred_label)
            #print(aliases)
        return bow

if __name__ == '__main__':
    if False :
        bow = BOWLanguageModel.train_from_dump('data/small.json.bz2',)
        print(sorted(bow.word_count.items(),
                    key=lambda x: bow._word_log_likelihood(x[0]),
                    reverse=True)[:10])
        bow.save('data/small.bow.pkl')
        bow2 = BOWLanguageModel()
        bow2.load('data/small.bow.pkl')
        print(sorted(bow2.word_count.items(),
                    key=lambda x: bow2._word_log_likelihood(x[0]),
                    reverse=True)[:10])
    if True :
        bow3 = BOWLanguageModel()
        bow3.load('data/latest-all.bow.pkl')
        print('Count of words in the language model: ' + str(len(bow3.word_count)))
        print('Total count of words in the language model: ' + str(bow3.total_count))
        print('Log quotient: ' + str(bow3.log_quotient))
        print('Log likelihood of "Nord": ' + str(bow3._word_log_likelihood('Nord')))
        print('Log likelihood of "Sud": ' + str(bow3._word_log_likelihood('Sud')))
        