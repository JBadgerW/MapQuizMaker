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

This project uses [uv](https://docs.astral.sh/uv/) for package management.

```
uv run map-quiz-maker
```

## How it works

1. Load an image.
2. Click on the image to mark a location; click an existing marker again to
   remove it (remaining markers renumber automatically).
3. Type the answer for each marker in the answer list.
4. Fill in Class / Title / Version / Instructions, and optionally set the
   number of versions, whether to save each as its own file, and whether to
   include a word bank.
5. Click "Build Quiz". A worksheet + answer-key PDF is generated and
   auto-compiled via the bundled [Typst](https://typst.app/) engine (no
   LaTeX install required) into `output/`.
