# Map Quiz Maker

I am a high school teacher in math and humanities. I am a big fan of paper
quizzes and also the practice of giving students as many cracks at any
particular formative assessment as they need to get the answers right. But I
also want them randomized to eliminate as much as possible the memorization
of a particular instrument.

The point of this little app is to import a map, allow the teacher to click
around at various points on the map, and create a question for each one of
the points. Then it should produce a bunch of different versions of a quiz
(as many as you ask it to) that will allow you to test students on the
features marked. It could conceivably be used to generate quizzes for any
type of image identification: maps, anatomy charts, artwork, etc.

## Running

From a checkout, using [uv](https://docs.astral.sh/uv/):

```
uv run map-quiz-maker
```

Or install it as a standalone tool, which puts `map-quiz-maker` on your PATH
and needs no checkout:

```
uv tool install .
map-quiz-maker
```

There is nothing else to install. The Typst engine, the worksheet template,
and the fonts the worksheet uses are all bundled, so quizzes typeset
identically on any machine -- no LaTeX, no Typst install, and no dependency
on which fonts happen to be present.

## How it works

1. Load a map image.
2. Click the map to mark a location, then type its answer. Markers renumber
   themselves automatically.
3. Drag a marker to move it, keeping its number and answer. Right-click a
   marker, press Delete, or use the × in the answer list to remove one.
   Ctrl+Z undoes any of it.
4. Fill in Class / Author / Title / Instructions, and optionally set the
   number of versions, whether to save each as its own file, and whether to
   include a word bank. Instructions print above the map; leave the field
   blank to omit them.
5. **Save** (Ctrl+S) keeps your work as an `.etqw` file you can reopen and
   edit later.
6. **Build Quiz PDF** (Ctrl+B) generates the shuffled versions and compiles
   them via the bundled [Typst](https://typst.app/) engine (no LaTeX install
   required), then tells you what was written and offers to open it. Long
   builds show progress and can be cancelled; the window stays responsive.

Selecting a location in one view highlights it in the other, so with thirty
markers you can still tell which row belongs to which point on the map.

## The `.etqw` file format

Quizzes are saved as `.etqw`, the same format used by my
`test_worksheet_generator` app, so a map quiz can be opened there and its
subsection dropped into a larger test or exam.

A saved quiz is one etqw document holding a single `fill_in_the_blank`
subsection: the map is the subsection's image stimulus and each location is
one question, with its answer inline in the stem as a `{{answer}}` marker.
The app's "include word bank" checkbox is the subsection's `show_word_bank`.

Two images travel inside the bundle. The stimulus (`map.png`) has the
numbers already drawn on it, because etqw renders an image as-is and has no
notion of a marker; the clean original travels beside it so this app can
reopen the document and move a marker. The marker coordinates ride in an
`x_mapquiz` key on the stimulus, which the etqw schemas accept and the etqw
app ignores.

One consequence worth knowing: **a quiz opened and re-saved in the etqw app
loses its marker positions**, coming back as a plain image-stimulus
subsection. etqw is the consumer; edit map quizzes here.

## Where quizzes are saved

"Build Quiz PDF" writes to `~/Documents/Map Quizzes` the first time. After that it
reuses whichever folder you last saved to, so "Save As..." to a different
folder becomes the new default. The remembered folder is kept in a small
settings file (`~/.config/map-quiz-maker/settings.json` on Linux, the
equivalent application-support folder on macOS and Windows); deleting it
resets the destination to the default.

Only finished PDFs are written there. The Typst source the app generates is
a build intermediate and is compiled from a temporary folder, so your quiz
folder holds nothing but the files you would actually print.

## The answer key

The key is written as its own PDF, `<name>_KEY.pdf`, so printing the
worksheets cannot hand out the answers. However the worksheets are split,
the key stays one file -- it is your reference copy. Tick "Put the answer
key in the same PDF" if you would rather have one document.

## Reproducible versions

Version 3 of a given quiz is the same paper every time you build it. The
shuffle comes from a seed stored in the `.etqw` file rather than from chance,
so a student who asks about the version they sat can be handed that exact
sheet again. Each key page carries a small build code (`71e1df-v1`) naming
the shuffle that produced it.

Editing the quiz -- adding a location, changing an answer -- changes what
every version contains, as you would expect. What is guaranteed is that
rebuilding an unchanged quiz reproduces it exactly.

## Licence

Map Quiz Maker is MIT licensed (`LICENSE.txt`). The bundled Linux Libertine
fonts are redistributed under the SIL Open Font License 1.1; their licence
travels with them in `src/map_quiz_maker/assets/fonts/LICENSE.txt`.
