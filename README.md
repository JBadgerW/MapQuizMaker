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

1. Load an image.
2. Click on the image to mark a location; click an existing marker again to
   remove it (remaining markers renumber automatically).
3. Type the answer for each marker in the answer list.
4. Fill in Class / Title / Instructions, and optionally set the number of
   versions, whether to save each as its own file, and whether to include a
   word bank. Instructions print above the map; leave the field blank to
   omit them.
5. Click "Save Quiz". A worksheet + answer-key PDF is generated and
   auto-compiled via the bundled [Typst](https://typst.app/) engine (no
   LaTeX install required), then a dialog tells you what was written and
   offers to open it.

## Where quizzes are saved

"Save Quiz" writes to `~/Documents/Map Quizzes` the first time. After that it
reuses whichever folder you last saved to, so "Save As..." to a different
folder becomes the new default. The remembered folder is kept in a small
settings file (`~/.config/map-quiz-maker/settings.json` on Linux, the
equivalent application-support folder on macOS and Windows); deleting it
resets the destination to the default.

Only finished PDFs are written there. The Typst source the app generates is
a build intermediate and is compiled from a temporary folder, so your quiz
folder holds nothing but the files you would actually print.

## Licence

Map Quiz Maker is MIT licensed (`LICENSE.txt`). The bundled Linux Libertine
fonts are redistributed under the SIL Open Font License 1.1; their licence
travels with them in `src/map_quiz_maker/assets/fonts/LICENSE.txt`.
