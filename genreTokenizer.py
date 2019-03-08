import unittest, re, string
import sqlite3 as lite


def allgrams(text):
    tokens = text.split(' ')
    return tokens

def flatten(iterable):
    return [item for subiterable in iterable for item in subiterable]


class GenreTokenizer(object):
    """
    Try to tokenize those pesky genre texts.
    """
    def __init__(self, method='bag-of-words'):
        self.whitespace_regex = re.compile(r'\s+')
        self.paren_regex = re.compile(r'\(.*?\)')
        self.split_regex = re.compile(r"""[/]+""")
        
        self.pre_split_replace = {" 'n' ": "'n'",
                                  " n' ": "'n'",
                                  }
        
        # this is stupid!  let the data speak for itself!
        self.simple_super_genres = frozenset([
                                        'acoustic',
                                        'alternative',
                                        'ambient',
                                        'aor',
                                        'classical',
                                        'crossover',
                                        'crust',
                                        'djent',
                                        'drone',
                                        'doom',
                                        'downtempo',
                                        'electronic',
                                        'electronica',
                                        'electronics',
                                        'experimental',
                                        'folk',
                                        'funk',
                                        'gothic',
                                        'grunge',
                                        'industrial',
                                        'medieval',
                                        'metal',
                                        'noise',
                                        'psybient',
                                        'psychedelic',
                                        'punk',
                                        'rock',
                                        'synth',
                                        'trance',
                                       ])
        self.compound_super_genre_prefix = frozenset(['neo', 'post', 'synth',])
        self.compound_super_genre_suffix = frozenset(['core', 'gaze', 'wave',
                                                     ])

        self.pre_split_words = frozenset(["rock 'n' roll",
                                          "death 'n' roll",
                                          "black 'n' roll",
                                          "thrash 'n' roll",
                                          'drum and bass',
                                          'a cappella',
                                          'middle eastern',
                                          'middle-eastern',
                                          'avant-garde',
                                          'j-rock',
                                          'd-beat',
                                          'new age',
                                          'nu-metal',
                                         ])

        self.drop_tokens = frozenset([None,'',
                            'influences',
                           'elements',
                           'of',
                           'and'])
        
        self.token_map = {'blackened': 'black',
                          'middle eastern': 'middle-eastern',
                          'neoclassic': 'neoclassical',
                          'operatic': 'opera',
                          'drum and bass': 'drum-and-bass',
                         }
        
        self.bad_tokens = frozenset([None,'',"n'","'n'",
                                    ])
        
        self.split_these_tokens = ['core', 'noise', 'grind', 'synth', 'wave',]
        
        self.method = method
        
    def tokenize(self, genre_text):
        genre_text = self.normalizeWhitespace(genre_text).lower()
        genre_text = self.removeParens(genre_text)
        texts = genre_text.split(',')
        
        # Check for any remaining "bad" characters
        for text in texts:
            if '(' in text or ')' in text or ',' in text:
                print(genre_text, texts)
                raise RuntimeError('bug')
        
        # do the messy split split
        if self.method == 'bag-of-words':
            tokens = [token for text in texts for token in self.splitBagOfWords(text)]
        elif self.method == 'split2':
            tokens = [token for text in texts for token in self.split2(text)]
        else:
            raise ValueError('unknown split method {}'.format(self.method))
        
        # Check for weird tokens
        for bad_token in self.bad_tokens:
            if bad_token in tokens or any(map(lambda token: len(token)==1, tokens)):
                print(genre_text, tokens)
                raise RuntimeError('bug')
        
        return tokens
    
    def normalizeWhitespace(self, text):
        """
        Remove leading and trailing whitespaces.  Use only one space between non-whitespace characters.
        """
        return re.sub(self.whitespace_regex, ' ', text).strip().rstrip()
    
    def removeParens(self, text):
        """
        Drop the stuff in parentheses.
        """
        return re.sub(self.paren_regex, '', text).strip().rstrip()
    
    #def is_super_genre(self, token):
    #    if token in self.simple_super_genres:
    #        return True
    #    
    #    for prefix in self.compound_super_genre_prefix:
    #        if token[0:len(prefix)] == prefix:
    #            return True
    #        
    #    for ending in self.compound_super_genre_suffix:
    #        if token[-len(ending):] == ending:
    #            return True

    #    return False
    
    #def split(self, text):
    #    """
    #    Do the split.  This is gonna be gross...
    #    """
    #    tokens = []
    #    
    #    text = self.normalizeWhitespace(text)
    #    
    #    # Do some replacements before any further tokenization
    #    for pat,sub in self.pre_split_replace.items():
    #        text = text.replace(pat,sub)
    #    
    #    # Grab these special cases first and remove them from the text
    #    pre_split_tokens = []
    #    for word in self.pre_split_words:
    #        if word in text:
    #            text = text.replace(word, ' ')
    #            pre_split_tokens.append(word)
    #            
    #    # Deal with modifiers like 'atmospheric black/folk metal'
    #    # We want 'atmospheric', 'atmospheric black', 'atmospheric black metal', 'black metal',
    #    # and 'folk metal' as tokens.
    #    splits = flatten(text.split(' ') for text in re.split('(/)', text)) # keep the / in the list
    #    
    #    # Drop certain tokens
    #    splits = [token for token in splits if token not in self.drop_tokens]
    #    
    #    if splits and splits[0] == '/': # weird edge case in the data
    #        splits.pop(0)
    #    
    #    #print(text)
    #    #print(splits)
    #    
    #    # Starting from the end, find a super genre and look ahead until the next super genre.
    #    # Then that slice is a "structured token".  Gotta handle what the slash means too.
    #    # Some genre texts have "modified super_genre with super_genre influences"; those super_genre
    #    # influences get counted as a separate super_genre token.
    #    structured_tokens = []
    #    i = len(splits)-1
    #    while i >= 0:
    #        token = splits[i]
    #        
    #        if token == '/': # weird edge case in the data, not this algorithm
    #            i -= 1
    #            continue
    #            
    #        #print(token)
    #        if not self.is_super_genre(token):
    #            print(text)
    #            print(splits)
    #            raise RuntimeError('token={} is not a super genre'.format(token))
    #            #print('skipping apparent super genre {}'.format(token))
    #        
    #        iend = i
    #        istart = i-1
    #        have_slash = False
    #        slash_is_modifier = False
    #        while istart >= 0:
    #            if splits[istart] == '/':
    #                have_slash = True
    #                if istart > 0:
    #                    if self.is_super_genre(splits[istart-1]):
    #                        # slash separates super genres
    #                        #print('slash separates super genres')
    #                        structured_tokens.append(splits[istart+1:iend+1])
    #                        i = istart - 1
    #                        break
    #                    else:
    #                        # slash separates modifiers
    #                        #print('slash separates modifiers')
    #                        slash_is_modifier = True
    #                        istart -= 1
    #                        continue
    #                else:
    #                    print(text)
    #                    print(splits)
    #                    raise RuntimeError('bug')
    #            else:
    #                if self.is_super_genre(splits[istart]) and slash_is_modifier:
    #                    structured_tokens.append(splits[istart+1:iend+1])
    #                    i = istart
    #                    break
    #                else:
    #                    istart -= 1
    #            
    #            #istart -= 1
    #        else:
    #            structured_tokens.append(splits[0:iend+1])
    #            i = istart
    #    
    #    print('text =', repr(text), ' -> structured_tokens =', structured_tokens)
    #    
    #    return tokens
    ##############################
    #    
    #    split_tokens = re.split(self.split_regex, text)
    #    
    #    for token in itertools.chain(pre_split_tokens, split_tokens):
    #        if token in self.drop_tokens:
    #            continue
    #        
    #        if token in self.token_map:
    #            token = self.token_map[token]
    #        
    #        tokens.append(token)
    #        
    #        #for base in self.split_these_tokens:
    #        #    if base in token:
    #        #        print('stuff')
    #    
    #    return tokens
    
    def split2(self, text):
        """
        Do the split.  This is gonna be gross...
        
        This assumes the following structure
        
        modifier modifier/modifier super_genre with modifier influences
        """
        # Do some replacements before any further tokenization
        for pat,sub in self.pre_split_replace.items():
            text = text.replace(pat,sub)
            
        # Deal with modifiers like 'atmospheric black/folk metal'
        # We want 'atmospheric', 'atmospheric black', 'atmospheric black metal', 'black metal',
        # and 'folk metal' as tokens.
        splits = flatten(re.split(r'( )', text) for text in re.split(r'(/)', text)) # keep the / in the list
        
        # Drop certain tokens
        splits = [token for token in splits if token not in self.drop_tokens]
        
        if splits and (splits[0] == '/' or splits[0] == ' '): # weird edge case in the data
            splits.pop(0)
        if splits and (splits[-1] == '/' or splits[-1] == ' '): # weird edge case in the data
            splits.pop(-1)
        
        print('text =', text)
        print('splits =', splits)
        
        extra_modifiers = []
        if 'with' in splits:
            ind = splits.index('with')
            extra_modifiers.extend(splits[ind+1:])
            splits = splits[0:ind]
            
            extra_modifiers = [token for token in extra_modifiers if token != ' ']
            print('extra_modifiers =', extra_modifiers)
            print('splits =', splits)
        
        super_genres = frozenset(['rock', 'metal'])
        
        def splitter(tokens, splits, i):
            # token is assumed to be a super genre here
            token = splits[i]
            
            # but sometimes the data entry is wrong...
            if token == ' ' or token == '/':
                print('Bug in data entry')
                splitter(tokens, splits, i-1)
                return
                
            #print("token={} isn't in super_genres set".format(token))
                
            
            if i > 0:
                if splits[i-1] == ' ':
                    # there are modifiers; collect them all
                    modifiers = [[]]
                    i1 = i-2
                    while i1 >= 0:
                        mod = splits[i1]
                        
                        if mod == ' ' or mod == '/': # bug in data entry
                            i1 -= 1
                            continue
                        
                        modifiers[-1].append(mod)
                        if i1 > 1:
                            if splits[i1-1] == ' ':
                                # compound modifier
                                pass
                                
                            elif splits[i1-1] == '/':
                                # end of current modifier
                                next_token = splits[i1-2]
                                if next_token in super_genres:
                                    print('next token is a super genre')
                                    break
                                else:
                                    modifiers.append([])
                                
                            else:
                                raise RuntimeError('bug')
                        else:
                            # Just one modifier and we're done
                            break
                        i1 -= 2
                    
                    # reverse order of modifiers to match up with text
                    modifiers = [[m for m in reversed(modifier)] for modifier in reversed(modifiers)]
                    
                    tokens.append([*modifiers, token])
                    splitter(tokens, splits, i1-2)
                    
                elif splits[i-1] == '/':
                    # token is a bare super genre
                    tokens.append(token)
                    splitter(tokens, splits, i-2)
                
                else:
                    raise RuntimeError()
            elif i == 0:
                # token is a bare super genre and we're done
                tokens.append(token)
        
        tokens = []
        splitter(tokens, splits, len(splits)-1)
        tokens = [token for token in reversed(tokens)]
        
        return tokens
    
    def splitBagOfWords(self, text):
        """
        Do the split.  This shouldn't be too bad.  Just a list of all words.
        """
        text = str(text)
        
        # Do some replacements before any further tokenization
        pre_split_replace = [#(" 'n' ", "-'n'-"),
                             #(" n' ", "-'n'-"),
                             #("'n'roll", "-'n'-roll"),
                             (" 'n' ", " "),
                             (" n' ", " "),
                             ("'n'roll", " roll"),
                             ('a cappella', 'a-cappella'),
                             ('post ', 'post-'),
                             ('\u200b', ''),
                             ('middle eastern', 'middle-eastern'),
                             ]
        for pat,sub in pre_split_replace:
            #text = text.replace(pat,sub)
            text = re.sub(pat,sub,text)
            
        # Deal with modifiers like 'atmospheric black/folk metal'
        # We want 'atmospheric', 'atmospheric black', 'atmospheric black metal', 'black metal',
        # and 'folk metal' as tokens.
        splits = flatten(text.split(' ') for text in text.split('/'))
        
        # Drop certain tokens
        drop_tokens = frozenset(['',None,'-',';',
                                 'with','influences','elements','of','and','music'])
        tokens = [token for token in splits if token not in drop_tokens]
        
        # Map certain tokens to other tokens (or list of tokens)
        # mainly to fix some easy things up
        map_tokens = {
            'core': ('hardcore',),
            'ebm-gothic': ('ebm', 'gothic'),
            'electro': ('electronic',),
            'electronica': ('electronic',),
            'electronics': ('electronic',),
            'hop': ('hip-hop',), # ???
            'neoclassical': ('neoclassic',),
            'operatic': ('opera',),
            'post-': ('post',),
            'stone': ('stoner',),
            }
        
        # populate if you want to split the cores
        map_core = {
            'blackened': ('black',),
            'breakcore': ('electronic', 'dance', 'hardcore'),
            'cybergrind': ('electronic', 'hardcore'),
            'crustcore': ('crust', 'hardcore'),
            'darkwave': ('dark', 'wave'),
            'deathrock': ('death', 'metal', 'rock'),
            'goregrind': ('gore', 'grind'),
            'jazz-fusion': ('jazz', 'fusion'),
            'mathcore': ('math', 'hardcore'),
            'neoclassic': ('new', 'classic'),
            'noisecore': ('noise', 'hardcore'),
            'noisegrid': ('noise', 'grind'),
            'post-black': ('post', 'black'),
            'post-doom': ('post', 'doom'),
            'post-grunge': ('post', 'grunge'),
            'post-hardcore': ('post', 'hardcore'),
            'post-industrial': ('post', 'industrial'),
            'post-metal': ('post', 'metal'),
            'post-punk': ('post', 'punk'),
            'post-rock': ('post', 'rock'),
            'post-sludge': ('post', 'sludge'),
            'powerviolence': ('power', 'violence'),
            'psychobilly': ('punk', 'rockabilly'),
            'slowcore': ('downtempo', 'core'),
            'synthpop': ('synth', 'pop'),
            'synthwave': ('synth', 'wave'),
            'thrashcore': ('thrash', 'core'),
            'trip-hop': ('trip', 'hip-hop', 'downtempo'),
            }
        
        def map_token_list(token_list, mapping):
            return flatten(mapping[token] if token in mapping else (token,) for token in token_list)
            #mapped_tokens = []
            #for token in token_list:
            #    if token in map:
            #        mapped_tokens.extend(map[token])
            #    else:
            #        mapped_tokens.append(token)
            #return mapped_tokens
        
        # Even split up these?
        #even_the_big_boys = {}
        #even_the_big_boys = {
        #    'deathcore': ('death', 'metal', 'hardcore'),
        #    'grindcore': ('grind', 'hardcore'),
        #    'metalcore': ('metal', 'hardcore'),
        #    }
        even_the_big_boys = {
            'deathcore': ('deathcore', 'death', 'metal', 'hardcore'),
            'grindcore': ('grindcore', 'grind', 'hardcore'),
            'metalcore': ('metalcore', 'metal', 'hardcore'),
            }
 
        
        tokens = map_token_list(tokens, map_tokens)
        tokens = map_token_list(tokens, map_core)
        tokens = map_token_list(tokens, even_the_big_boys)
        
        return tokens
    

class Test(unittest.TestCase):
    def testSomeExamples(self):
        method = 'split2'
        
        example_text_tokens = [('folk metal/rock',
                                [[['folk'], 'metal'], 'rock']),
                               ('melodic heavy metal/hard rock',
                                [[['melodic', 'heavy'], 'metal'], [['hard'], 'rock']]),
                               ]
        
        tokenizer = GenreTokenizer(method=method)
        for text, ref_tokens in example_text_tokens:
            test_tokens = tokenizer.tokenize(text)
            
            print('='*40)
            print('text        =', text)
            print('ref_tokens  =', ref_tokens)
            print('test_tokens =', test_tokens)
            print('='*40)
    
    def testRun(self):
        method = 'split2'

if __name__ == '__main__':
    unittest.main()