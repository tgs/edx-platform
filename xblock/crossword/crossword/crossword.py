"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, Float, Dict, String, Boolean
from xblock.fragment import Fragment
import json

@XBlock.needs("i18n")
class CrosswordXBlock(XBlock):
    """
    TO-DO: document what your XBlock does.
    """

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    display_name = String(
        scope=Scope.settings,
        display_name="A Display Name",
        help="Display name for the crossword",
        default="Crossword",
    )

    width = Integer(
        scope=Scope.settings,
        display_name="Table Width",
        help="Width of the crossword puzzle table",
        default=20
    )

    height = Integer(
        scope=Scope.settings,
        display_name="Table Height",
        help="Height of the crossword puzzle table",
        default=20
    )

    time_to_generate_crossword = Float(
        scope=Scope.settings,
        display_name="Time to Generate",
        help="Amount of time, in seconds, to generate the crossword puzzle",
        default=2.0
    )

    only_check_once = Boolean(
        scope=Scope.settings,
        display_name="Only Check Once",
        help="Whether or not the student can check their answer only once",
        default=2.0
    )

    words = Dict(
        scope=Scope.settings,
        display_name="Clues and Words",
        help="The words for the crossword with clues and answers",
        default={
            "saffron2": "The dried, orange yellow plant used to as dye and as a cooking spice.",
            "pumpernickel": "Dark, sour bread made from coarse ground rye.",
            "leaven": "An agent, such as yeast, that cause batter or dough to rise..",
            "coda": "Musical conclusion of a movement or composition.",
            "paladin": "A heroic champion or paragon of chivalry.",
            "syncopation": "Shifting the emphasis of a beat to the normally weak beat.",
            "albatross": "A large bird of the ocean having a hooked beek and long, narrow wings.",
            "harp": "Musical instrument with 46 or more open strings played by plucking.",
            "piston": "A solid cylinder or disk that fits snugly in a larger cylinder and moves \
                under pressure as in an engine.",
            "caramel": "A smooth chery candy made from suger, butter, cream or milk with flavoring.",
            "coral": "A rock-like deposit of organism skeletons that make up reefs.",
            "dawn": "The time of each morning at which daylight begins.",
            "pitch": "A resin derived from the sap of various pine trees.",
            "fjord": "A long, narrow, deep inlet of the sea between steep slopes.",
            "lip": "Either of two fleshy folds surrounding the mouth.",
            "lime": "The egg-shaped citrus fruit having a green coloring and acidic juice.",
            "mist": "A mass of fine water droplets in the air near or in contact with the ground.",
            "plague": "A widespread affliction or calamity.",
            "yarn": "A strand of twisted threads or a long elaborate narrative.",
            "snicker": "A snide, slightly stifled laugh."
        }
    )

    student_crossword = Dict(
        scope=Scope.user_state,
        help="Crossword generated for this user",
        default=None,
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @property
    def non_editable_metadata_fields(self):
        return [CrosswordXBlock.tags, CrosswordXBlock.name]

    @property
    def editable_metadata_fields(self):
        """
        Returns the metadata fields to be edited in Studio. These are fields with scope `Scope.settings`.

        Can be limited by extending `non_editable_metadata_fields`.
        """
        def jsonify_value(field, json_choice):
            if isinstance(json_choice, dict):
                json_choice = dict(json_choice)  # make a copy so below doesn't change the original
                if 'display_name' in json_choice:
                    json_choice['display_name'] = get_text(json_choice['display_name'])
                if 'value' in json_choice:
                    json_choice['value'] = field.to_json(json_choice['value'])
            else:
                json_choice = field.to_json(json_choice)
            return json_choice

        def get_text(value):
            """Localize a text value that might be None."""
            if value is None:
                return None
            else:
                return self.runtime.service(self, "i18n").ugettext(value)

        metadata_fields = {}

        # Only use the fields from this class, not mixins
        fields = getattr(self, 'unmixed_class', self.__class__).fields

        for field in fields.values():

            if field.scope != Scope.settings or field in self.non_editable_metadata_fields:
                continue

            # gets the 'default_value' and 'explicitly_set' attrs
            metadata_fields[field.name] = self.runtime.get_field_provenance(self, field)
            metadata_fields[field.name]['field_name'] = field.name
            metadata_fields[field.name]['display_name'] = get_text(field.display_name)
            metadata_fields[field.name]['help'] = get_text(field.help)
            metadata_fields[field.name]['value'] = field.read_json(self)

            # We support the following editors:
            # 1. A select editor for fields with a list of possible values (includes Booleans).
            # 2. Number editors for integers and floats.
            # 3. A generic string editor for anything else (editing JSON representation of the value).
            editor_type = "Generic"
            values = field.values
            if isinstance(values, (tuple, list)) and len(values) > 0:
                editor_type = "Select"
                values = [jsonify_value(field, json_choice) for json_choice in values]
            elif isinstance(field, Integer):
                editor_type = "Integer"
            elif isinstance(field, Float):
                editor_type = "Float"
            elif isinstance(field, List):
                editor_type = "List"
            elif isinstance(field, Dict):
                editor_type = "Dict"
            # elif isinstance(field, RelativeTime):
            #     editor_type = "RelativeTime"
            metadata_fields[field.name]['type'] = editor_type
            metadata_fields[field.name]['options'] = [] if values is None else values

        return metadata_fields

    def studio_view(self, context):
        # html = self.resource_string("static/html/crossword_studio.html")
        fields_dump = json.dumps(self.editable_metadata_fields)
        html = u'<div class="wrapper-comp-settings metadata_edit" data-metadata=\'' + fields_dump + '\'></div>'

        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/crossword.css"))
        frag.add_javascript(self.resource_string("static/js/src/crossword.js"))
        frag.initialize_js('CrosswordXBlock')
        return frag

    def is_studio_view(self, context):
        return (context is not None) and ('runtime_type' in context) and (context['runtime_type'] == 'studio')

    def student_view(self, context=None):
        """
        The primary view of the CrosswordXBlock, shown to students
        when viewing courses.
        """
        studio_view = self.is_studio_view(context)

        if studio_view or self.student_crossword is None:
            crossword = Crossword(self.width, self.height, '-', 5000, [(key, value) for key, value in self.words.iteritems()])
            crossword.compute_crossword(self.time_to_generate_crossword)
            if not studio_view:
                # store the generated crossword for the student so they get the same one each time
                self.student_crossword = crossword.to_json()
                self.save()
        elif not studio_view:
            crossword = Crossword.from_json(self.student_crossword)

        sorted_words = [word for word in crossword.current_word_list if not word.vertical]
        last_horizontal = len(sorted_words) - 1
        sorted_words += [word for word in crossword.current_word_list if word.vertical]

        words = len(sorted_words)
        word_length = 'new Array(' + ','.join([str(word.length) for word in sorted_words]) + ')'
        word_arr = 'new Array("' + '","'.join([word.word.upper() for word in sorted_words]) + '")'
        clue = 'new Array("' + '","'.join([word.clue for word in sorted_words]) + '")'
        wordx = 'new Array(' + ','.join([str(word.col - 1) for word in sorted_words]) + ')'
        wordy = 'new Array(' + ','.join([str(word.row - 1) for word in sorted_words]) + ')'

        # table = ""
        # row = col = 0
        # for line in crossword.solution().splitlines():
        #     table += "<tr>"
        #     for char in line:
        #         if char == ' ':
        #             continue
        #         elif char == '-':
        #             table += "<td></td>"
        #         else:
        #             table += '<td id="c' + ("%03d" % col) + ("%03d" % row) + '" class="box boxnormal_unsel" onclick="SelectThisWord(event);">&nbsp;</td>'
        #         col += 1
        #     table += "</tr>"
        #     row += 1

        html = self.resource_string("static/html/crossword.html")
        # for some reason the templates weren't working, so I'm doing it manually
        frag = Fragment(
            html.replace("{self.width}", str(self.width))
            .replace("{self.height}", str(self.height))
            .replace("{self.words}", str(words))
            .replace("{self.word_length}", word_length)
            .replace("{self.word}", word_arr)
            .replace("{self.clue}", clue)
            .replace("{self.wordx}", wordx)
            .replace("{self.wordy}", wordy)
            .replace("{self.only_check_once}", "true" if self.only_check_once else "false")
            .replace("{self.location}", unicode(self.location).replace('+', '_').replace(':', '_'))
            .replace("{last_horizontal}", str(last_horizontal))
        )
        frag.add_css(self.resource_string("static/css/crossword.css"))
        frag.add_javascript(self.resource_string("static/js/src/crossword.js"))
        frag.initialize_js('CrosswordXBlock')
        return frag


    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("CrosswordXBlock",
             """<vertical_demo>
                <crossword/>
                </vertical_demo>
             """),
        ]

import random, re, time, string
from copy import copy as duplicate

class Crossword(object):
    def __init__(self, cols, rows, empty = '-', maxloops = 2000, available_words=[]):
        self.cols = cols
        self.rows = rows
        self.empty = empty
        self.maxloops = maxloops
        self.available_words = available_words
        self.randomize_word_list()
        self.current_word_list = []
        self.debug = 0
        self.clear_grid()

    SERIALIZED_FIELDS = ['cols', 'rows']
    def to_json(self):
        json_value = {
            attribute: getattr(self, attribute)
            for attribute in self.SERIALIZED_FIELDS
        }
        json_value.update(
            {'current_word_list': [word.to_json() for word in self.current_word_list]}
        )
        return json_value

    @staticmethod
    def from_json(json_value):
        crossword = Crossword(0, 0)
        for key in json_value:
            if key in crossword.SERIALIZED_FIELDS:
                setattr(crossword, key, json_value[key])
        if 'current_word_list' in json_value:
            word_json_list = json_value['current_word_list']
            crossword.current_word_list = [
                Word.from_json(word_json)
                for word_json in word_json_list
            ]
        return crossword

    def clear_grid(self): # initialize grid and fill with empty character
        self.grid = []
        for i in range(self.rows):
            ea_row = []
            for j in range(self.cols):
                ea_row.append(self.empty)
            self.grid.append(ea_row)

    def randomize_word_list(self): # also resets words and sorts by length
        temp_list = []
        for word in self.available_words:
            if isinstance(word, Word):
                temp_list.append(Word(word.word, word.clue))
            else:
                temp_list.append(Word(word[0], word[1]))
        random.shuffle(temp_list) # randomize word list
        temp_list.sort(key=lambda i: len(i.word), reverse=True) # sort by length
        self.available_words = temp_list

    def compute_crossword(self, time_permitted = 1.00, spins=2):
        time_permitted = float(time_permitted)

        count = 0
        copy = Crossword(self.cols, self.rows, self.empty, self.maxloops, self.available_words)

        start_full = float(time.time())
        while (float(time.time()) - start_full) < time_permitted or count == 0: # only run for x seconds
            self.debug += 1
            copy.current_word_list = []
            copy.clear_grid()
            copy.randomize_word_list()
            x = 0
            while x < spins: # spins; 2 seems to be plenty
                for word in copy.available_words:
                    if word not in copy.current_word_list:
                        copy.fit_and_add(word)
                x += 1

            # buffer the best crossword by comparing placed words
            if len(copy.current_word_list) > len(self.current_word_list):
                self.current_word_list = copy.current_word_list
                self.grid = copy.grid
            count += 1
        return

    def suggest_coord(self, word):
        count = 0
        coordlist = []
        glc = -1
        for given_letter in word.word: # cycle through letters in word
            glc += 1
            rowc = 0
            for row in self.grid: # cycle through rows
                rowc += 1
                colc = 0
                for cell in row: # cycle through  letters in rows
                    colc += 1
                    if given_letter == cell: # check match letter in word to letters in row
                        try: # suggest vertical placement
                            if rowc - glc > 0: # make sure we're not suggesting a starting point off the grid
                                if ((rowc - glc) + word.length) <= self.rows: # make sure word doesn't go off of grid
                                    coordlist.append([colc, rowc - glc, 1, colc + (rowc - glc), 0])
                        except: pass
                        try: # suggest horizontal placement
                            if colc - glc > 0: # make sure we're not suggesting a starting point off the grid
                                if ((colc - glc) + word.length) <= self.cols: # make sure word doesn't go off of grid
                                    coordlist.append([colc - glc, rowc, 0, rowc + (colc - glc), 0])
                        except: pass
        # example: coordlist[0] = [col, row, vertical, col + row, score]
        #print word.word
        #print coordlist
        new_coordlist = self.sort_coordlist(coordlist, word)
        #print new_coordlist
        return new_coordlist

    def sort_coordlist(self, coordlist, word): # give each coordinate a score, then sort
        new_coordlist = []
        for coord in coordlist:
            col, row, vertical = coord[0], coord[1], coord[2]
            coord[4] = self.check_fit_score(col, row, vertical, word) # checking scores
            if coord[4]: # 0 scores are filtered
                new_coordlist.append(coord)
        random.shuffle(new_coordlist) # randomize coord list; why not?
        new_coordlist.sort(key=lambda i: i[4], reverse=True) # put the best scores first
        return new_coordlist

    def fit_and_add(self, word): # doesn't really check fit except for the first word; otherwise just adds if score is good
        fit = False
        count = 0
        coordlist = self.suggest_coord(word)

        while not fit and count < self.maxloops:

            if len(self.current_word_list) == 0: # this is the first word: the seed
                # top left seed of longest word yields best results (maybe override)
                vertical, col, row = random.randrange(0, 2), 1, 1
                '''
                # optional center seed method, slower and less keyword placement
                if vertical:
                    col = int(round((self.cols + 1)/2, 0))
                    row = int(round((self.rows + 1)/2, 0)) - int(round((word.length + 1)/2, 0))
                else:
                    col = int(round((self.cols + 1)/2, 0)) - int(round((word.length + 1)/2, 0))
                    row = int(round((self.rows + 1)/2, 0))
                # completely random seed method
                col = random.randrange(1, self.cols + 1)
                row = random.randrange(1, self.rows + 1)
                '''

                if self.check_fit_score(col, row, vertical, word):
                    fit = True
                    self.set_word(col, row, vertical, word, force=True)
            else: # a subsquent words have scores calculated
                try:
                    col, row, vertical = coordlist[count][0], coordlist[count][1], coordlist[count][2]
                except IndexError: return # no more cordinates, stop trying to fit

                if coordlist[count][4]: # already filtered these out, but double check
                    fit = True
                    self.set_word(col, row, vertical, word, force=True)

            count += 1
        return

    def check_fit_score(self, col, row, vertical, word):
        '''
        And return score (0 signifies no fit). 1 means a fit, 2+ means a cross.

        The more crosses the better.
        '''
        if col < 1 or row < 1:
            return 0

        count, score = 1, 1 # give score a standard value of 1, will override with 0 if collisions detected
        for letter in word.word:
            try:
                active_cell = self.get_cell(col, row)
            except IndexError:
                return 0

            if active_cell == self.empty or active_cell == letter:
                pass
            else:
                return 0

            if active_cell == letter:
                score += 1

            if vertical:
                # check surroundings
                if active_cell != letter: # don't check surroundings if cross point
                    if not self.check_if_cell_clear(col+1, row): # check right cell
                        return 0

                    if not self.check_if_cell_clear(col-1, row): # check left cell
                        return 0

                if count == 1: # check top cell only on first letter
                    if not self.check_if_cell_clear(col, row-1):
                        return 0

                if count == len(word.word): # check bottom cell only on last letter
                    if not self.check_if_cell_clear(col, row+1):
                        return 0
            else: # else horizontal
                # check surroundings
                if active_cell != letter: # don't check surroundings if cross point
                    if not self.check_if_cell_clear(col, row-1): # check top cell
                        return 0

                    if not self.check_if_cell_clear(col, row+1): # check bottom cell
                        return 0

                if count == 1: # check left cell only on first letter
                    if not self.check_if_cell_clear(col-1, row):
                        return 0

                if count == len(word.word): # check right cell only on last letter
                    if not self.check_if_cell_clear(col+1, row):
                        return 0


            if vertical: # progress to next letter and position
                row += 1
            else: # else horizontal
                col += 1

            count += 1

        return score

    def set_word(self, col, row, vertical, word, force=False): # also adds word to word list
        if force:
            word.col = col
            word.row = row
            word.vertical = vertical
            self.current_word_list.append(word)

            for letter in word.word:
                self.set_cell(col, row, letter)
                if vertical:
                    row += 1
                else:
                    col += 1
        return

    def set_cell(self, col, row, value):
        self.grid[row-1][col-1] = value

    def get_cell(self, col, row):
        return self.grid[row-1][col-1]

    def check_if_cell_clear(self, col, row):
        try:
            cell = self.get_cell(col, row)
            if cell == self.empty:
                return True
        except IndexError:
            pass
        return False

    def solution(self): # return solution grid
        outStr = ""
        for r in range(self.rows):
            for c in self.grid[r]:
                outStr += '%s ' % c
            outStr += '\n'
        return outStr

    def word_find(self): # return solution grid
        outStr = ""
        for r in range(self.rows):
            for c in self.grid[r]:
                if c == self.empty:
                    outStr += '%s ' % string.lowercase[random.randint(0,len(string.lowercase)-1)]
                else:
                    outStr += '%s ' % c
            outStr += '\n'
        return outStr

    def order_number_words(self): # orders words and applies numbering system to them
        self.current_word_list.sort(key=lambda i: (i.col + i.row))
        count, icount = 1, 1
        for word in self.current_word_list:
            word.number = count
            if icount < len(self.current_word_list):
                if word.col == self.current_word_list[icount].col and word.row == self.current_word_list[icount].row:
                    pass
                else:
                    count += 1
            icount += 1

    def display(self, order=True): # return (and order/number wordlist) the grid minus the words adding the numbers
        outStr = ""
        if order:
            self.order_number_words()

        copy = self

        for word in self.current_word_list:
            copy.set_cell(word.col, word.row, word.number)

        for r in range(copy.rows):
            for c in copy.grid[r]:
                outStr += '%s ' % c
            outStr += '\n'

        outStr = re.sub(r'[a-z]', ' ', outStr)
        return outStr

    def word_bank(self):
        outStr = ''
        temp_list = duplicate(self.current_word_list)
        random.shuffle(temp_list) # randomize word list
        for word in temp_list:
            outStr += '%s\n' % word.word
        return outStr

    def legend(self): # must order first
        outStr = ''
        for word in self.current_word_list:
            outStr += '%d. (%d,%d) %s: %s\n' % (word.number, word.col, word.row, word.down_across(), word.clue )
        return outStr

class Word(object):
    def __init__(self, word=None, clue=None):
        self.word = re.sub(r'\s', '', word.lower() if word else '')
        self.clue = clue
        self.length = len(self.word)
        # the below are set when placed on board
        self.row = None
        self.col = None
        self.vertical = None
        self.number = None

    def down_across(self): # return down or across
        if self.vertical:
            return 'down'
        else:
            return 'across'

    def __repr__(self):
        return self.word

    SERIALIZED_FIELDS = ['word', 'clue', 'length', 'row', 'col', 'vertical', 'number']
    def to_json(self):
        return {
            attribute: getattr(self, attribute)
            for attribute in self.SERIALIZED_FIELDS
        }

    @staticmethod
    def from_json(json_value):
        word = Word()
        for key in json_value:
            if key in word.SERIALIZED_FIELDS:
                setattr(word, key, json_value[key])
        return word