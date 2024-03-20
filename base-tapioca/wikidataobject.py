import requests
import json
from geopy.distance import distance

class WikidataObject :

    def __init__(self, uri = None, jsondata = None, coordinates=None,):
        self.uri = uri
        self.coordinates = coordinates
        self.json = jsondata

    def __repr__(self):
        return '<WikidataItemDocument {}>'.format(self.json.get('id') or self.uri or '(unknown qid)')

    def __iter__(self):
        return self.json.__iter__()

    def request_json(self, store = False):
        """
        For a given URI of a WikidataObject,
        returns the JSON data of the object,
        and stores it in self.json if store is True
        """
        
        try:
            url = f'https://www.wikidata.org/wiki/Special:EntityData/{self.uri}.json'
            response = requests.get(url)
            data = response.json()
            
            if store:
                self.json = data

            return data

        except Exception as e:
            print('Error requesting JSON at URL:', url)
            print(e)

            return None
        
    def get_coord(self, store = False):
        """
        Returns the coordinates of the WikidataObject
        - from self.json if any
        - from a request to the Wikidata API otherwise (and stores it in self.json)
        stores it in self.coordinates if store is True
        """
        if self.json:
            try :
                self.coordinates = self.json['entities'][list(self.json['entities'].keys())[0]]['claims']['P625'][0]['mainsnak']['datavalue']['value']
            except :
                print('Error getting coordinates from JSON')
                self.coordinates = 'ERROR_COORDINATES'
                pass

        else :
            self.json = self.request_json(store = True)
            self.get_coord(store = True)

        return self.coordinates
    
    # method to compute a distance to another WikidataObject
    def distance_to(self, other):
        """
        Returns the distance between the coordinates of self and other
        """
        if self.coordinates and other.coordinates:
            d = distance(self.coordinates, other.coordinates).km
            return d
        else:
            return None
    
        
    
