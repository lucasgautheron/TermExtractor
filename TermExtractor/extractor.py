import nltk
import re
import numpy as np
import multiprocessing as mp

from functools import partial

from typing import List, Union

from unidecode import unidecode


class TermExtractor:
    DEFAULT_PATTERNS = [
        ["JJ.*"],
        ["NN.*"],
        ["JJ.*", "NN.*"],
        ["JJ.*", "NN.*", "NN.*"],
        ["JJ.*", "NN", "CC", "NN.*"],
        ["JJ.*", "NN.*", "JJ.*", "NN.*"],
        ["JJ.*", "NN.*", "IN", "DT", "NN.*"],
        # ["JJ.*", "VBN", "VBG", "NN.*"],
        # ["RB.*", "JJ.*", "NN.*", "NN.*"],
        # ["JJ.*", "NN.*", "IN", "PRP", "NN.*"],
    ]

    def __init__(self, abstracts: List[str], patterns: List[str] = None, limit_redundancy: bool = False):
        self.abstracts = list(map(lambda x: x.lower(), abstracts))
        self.patterns = self.DEFAULT_PATTERNS if patterns is None else patterns
        self.limit_redundancy = bool(limit_redundancy)

    def normalize_text(text: str) -> str:
        return unidecode(text).lower()

    def add_patterns(self, patterns: List[str]):
        self.patterns += patterns

    def tokens(self, lemmatize: bool = False, split_sentences: bool = False, threads: int = 0) -> Union[List[List[str]],List[List[List[str]]]]:
        if threads == 1:
            tokns = list(map(self.tokens_from_text, self.abstracts))
        else:
            pool = mp.Pool(processes=mp.cpu_count() if threads <= 0 else threads)
            tokns = pool.map(partial(self.tokens_from_text, split_sentences), self.abstracts)

        if lemmatize:
            lemmatizer = nltk.stem.WordNetLemmatizer()

            for i, doc in enumerate(tokns):
                tokns[i] = [list(map(lemmatizer.lemmatize, sentence)) for sentence in doc]

        return tokns

    def tokens_from_text(self, split_sentences: bool, text: str) -> Union[List[str], List[List[str]]]:
        stop_words = nltk.corpus.stopwords.words("english")

        if split_sentences:
            tokens = []
            sentences = nltk.sent_tokenize(text)

            for sentence in sentences:
                _tokens = nltk.word_tokenize(sentence)
                _tokens = [token for token in _tokens if token not in stop_words]
                tokens.append(_tokens)
        else:
            tokens = nltk.word_tokenize(text)
            tokens = [token for token in tokens if token not in stop_words]

        return tokens

    def ngrams(
        self,
        lemmatize: bool = False,
        lemmatize_ngrams: bool = False,
        split_sentences: bool = False,
        threads: int = 0
    ) -> List[List[List[str]]]:

        self.split_sentences = bool(split_sentences)
        self.patterns = sorted(self.patterns, key=len, reverse=True)

        _ngrams = None

        if threads == 1:
            _ngrams = list(map(self.ngrams_from_text, self.abstracts))
        else:
            pool = mp.Pool(processes=mp.cpu_count() if threads <= 0 else threads)
            _ngrams = pool.map(self.ngrams_from_text, self.abstracts)

        if lemmatize:
            lemmatizer = nltk.stem.WordNetLemmatizer()

            if lemmatize_ngrams:
                    if self.split_sentences:
                        _ngrams = [
                            [
                                [
                                    list(map(lemmatizer.lemmatize, ngram))
                                    for ngram in sentence
                                ]
                                for sentence in abstract_ngrams
                            ]
                            for abstract_ngrams in _ngrams
                        ]
                    else:
                        _ngrams = [
                            [
                                list(map(lemmatizer.lemmatize, ngram))
                                for ngram in abstract_ngrams
                            ]
                            for abstract_ngrams in _ngrams
                        ]
            else:
                if self.split_sentences:
                    _ngrams = [
                        [
                            [
                                ngram if len(ngram) > 1 else [lemmatizer.lemmatize(ngram[0])]
                                for ngram in sentence
                            ]
                            for sentence in abstract_ngrams
                        ]
                        for abstract_ngrams in _ngrams
                    ]
                else:
                    _ngrams = [
                        [
                            ngram if len(ngram) > 1 else [lemmatizer.lemmatize(ngram[0])]
                            for ngram in abstract_ngrams
                        ]
                        for abstract_ngrams in _ngrams
                    ]

        return _ngrams

    def ngrams_from_text(self, text: str) -> List[List[str]]:
        matches = []
        sentences = nltk.sent_tokenize(text)

        for sentence in sentences:
            if self.split_sentences:
                sent_matches = []

            tokens = nltk.word_tokenize(sentence)
            tokens = nltk.pos_tag(tokens)
            
            expressions_positions = []

            for i, t in enumerate(tokens):
                token, tag = t

                for pattern in self.patterns:                    
                    length = len(pattern)
                    tags = list(map(lambda x: x[1], tokens[i : i + length]))

                    if len(tags) != length:
                        continue

                    if all([re.match(pat, tags[j]) for j, pat in enumerate(pattern)]):
                        keep = True

                        if self.limit_redundancy:
                            for a, b in expressions_positions:
                                if i >= a and i+length <= b:
                                    keep = False
                                    break

                        if keep == False:
                            continue
                        
                        if self.split_sentences:
                            sent_matches.append(
                                list(map(lambda x: x[0], tokens[i : i + length]))
                            )
                        else:
                            matches.append(
                                list(map(lambda x: x[0], tokens[i : i + length]))
                            )

                        expressions_positions.append(
                            (i, i+length)
                        )

            if self.split_sentences:
                matches.append(sent_matches)
            
        return matches