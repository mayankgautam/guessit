#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from guessit.plugins.transformers import Transformer
from guessit.country import Country
from guessit import Guess
from guessit.textutils import iter_words
from guessit.matcher import GuessFinder, found_guess
from guessit.language import LNG_COMMON_WORDS


class GuessCountry(Transformer):
    def __init__(self):
        Transformer.__init__(self, -170)
        self.replace_language = frozenset(['uk'])

    def supported_properties(self):
        return ['country']

    def should_process(self, mtree, options=None):
        options = options or {}
        return 'nocountry' not in options.keys()

    def _scan_country(self, country, strict=False):
        """
        Find a country if it is at the start or end of country string
        """
        words_match = list(iter_words(country.lower()))
        s = ""
        start = None

        for word_match in words_match:
            if not start:
                start = word_match.start(0)
            s += word_match.group(0)
            try:
                return Country(s, strict=True), (start, word_match.end(0))
            except ValueError:
                continue

        words_match.reverse()
        s = ""
        end = None
        for word_match in words_match:
            if not end:
                end = word_match.end(0)
            s = word_match.group(0) + s
            try:
                return Country(s, strict=True), (word_match.start(0), end)
            except ValueError:
                continue

        return Country(country, strict=strict), None

    def is_valid_country(self, country):
        return country.english_name.lower() not in LNG_COMMON_WORDS and country.alpha2.lower() not in LNG_COMMON_WORDS and country.alpha3.lower() not in LNG_COMMON_WORDS

    def guess_country(self, string, node=None, options=None):
        c = string.strip().lower()
        if not c in LNG_COMMON_WORDS:
            try:
                country, country_span = self._scan_country(c, True)
                if self.is_valid_country(country):
                    guess = Guess(country=country, confidence=1.0, input=node.value, span=(country_span[0] + 1, country_span[1] + 1))
                    return guess
            except ValueError:
                pass
        return None, None

    def process(self, mtree, options=None):
        GuessFinder(self.guess_country, None, self.log, options).process_nodes(mtree.unidentified_leaves())
        for node in mtree.leaves_containing('language'):
            c = node.clean_value.lower()
            if c in self.replace_language:
                node.guess.set('language', None)
                try:
                    country = Country(c, strict=True)
                    if self.is_valid_country(country):
                        guess = Guess(country=country, confidence=0.9, input=node.value, span=node.span)
                        found_guess(node, guess)
                except ValueError:
                    pass

    def post_process(self, mtree, options=None, *args, **kwargs):
        # if country is in the guessed properties, make it part of the series name
        series_leaves = mtree.leaves_containing('series')
        country_leaves = mtree.leaves_containing('country')

        if series_leaves and country_leaves:
            country_leaf = country_leaves[0]
            for serie_leaf in series_leaves:
                serie_leaf.guess['series'] += ' (%s)' % country_leaf.guess['country'].alpha2.upper()
