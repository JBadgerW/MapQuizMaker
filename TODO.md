TODOs for MapQuizMaker
======================

- [x] (7/29) Needs refactoring to use Pathlib.

- [x] (7/29) I want to significantly simplify the files that make up the app.
I want to lean on uv for package management, etc, and bring the file names and
duties into line with standard Python best-practices.

- [x] (7/29) I don't particularly like the basic Tkinter look. Advise on 
tkinter styling templates that might be nice to look at.

- [x] (7/29) I don't like the terminal output tracking the GUI. People who use 
the GUI are going to be weirded out by it.

- [x] (7/29) The Class, Title, Version, and Instruction fields are very poorly 
laid out. I think I was going for the most basic, easiest-to-implement layout,
but it looks not very professional.

- [x] (7/29) The Instructions field should really be a paragraph, not just a
small field that looks like it would take a single word.

- [x] (7/29) I've been moving my typesetting workflow to Typst as much as possible.
If it is possible to accomplish the same thing with Typst as I have here with
LaTeX, I want to refactor to use Typst instead. That way, I can bundle the Typst
Python library with it and using the app won't require a massive LaTeX install.

- [x] (7/29) The app should automatically compile the output it creates (ideally
with Typst).

- [x] (7/29) There should be an option to automatically save n versions of the 
quiz with automatic version numbering. There should be an option (default 
unselected) to save each as a separate file.

- [x] (7/29) When the user deletes one of the locations on the map, the rest of
the numbers should reorder. There's no reason for any particular order since 
the numbers are going to change on the quizzes anyway.

- [x] (7/29) There should be an option to print a word-bank at the beginning of
the questions section after the image.

Architecture review follow-up (9/2)
-----------------------------------

Stage 1 -- stop the bleeding:

- [x] (9/2) Answers committed on every keystroke instead of on focus-out.
Adding a marker rebuilds the answer rows, so anything typed for the previous
marker was silently destroyed on every click-type-click cycle.

- [x] (9/2) Quizzes save to ~/Documents/Map Quizzes (remembering the
last-used folder) instead of a path relative to the working directory, and a
completion dialog says what was written with Open PDF / Show in Folder.

- [x] (9/2) Instructions print above the map again, and are suppressed
entirely when the field is blank.

- [x] (9/2) sanitize_filename whitelists characters, so a title like
"Rivers/Mountains" or "Ch. 4: Greece" can no longer corrupt the output path.

- [x] (9/2) Pulled forward from stage 4: the generated .typ is written to a
temp directory and the source image is referenced in place rather than
copied, so the output folder holds only finished PDFs.

Remaining stages:

Stage 2 -- make it installable:

- [x] (9/2) Template and fonts moved into the package and loaded via
importlib.resources, so they ship in the wheel. An installed copy could not
build a quiz at all before this: the template path was derived by walking up
from __file__, and assets/ was never packaged.

- [x] (9/2) Linux Libertine bundled (regular/bold/italic/bold-italic, OFL)
and passed to Typst with ignore_system_fonts, so worksheets no longer
re-flow on a machine that lacks the font.

- [x] (9/2) Typst now compiles from a self-contained sandbox directory that
is also its project root, which retired the root="/" escape hatch.

Stage 3 -- give it a document:

- [x] (9/2) Marker positions stored as fractions of the image (0..1) with a
top-left origin, replacing centimetres tied to a fixed print width and the
bottom-left origin inherited from the old TikZ output.

- [x] (9/2) QuizDocument is the single authoritative state object: metadata,
image, markers, build options, dirty flag and undo/redo history. Panels hold
no marker state and reconcile against it instead of rebuilding.

- [x] (9/2) Saves as .etqw so a map quiz can be imported into the
test_worksheet_generator app. Verified against that project's own schemas,
loader and Typst renderer in tests/test_etqw.py (skipped if it isn't checked
out beside this one).

- [x] (9/2) Menu bar with New / Open / Open Recent / Save / Save As, a dirty
marker in the title, an unsaved-changes prompt on close, and undo/redo.

- [x] (9/2) Markers can be dragged to move them; the map and answer list are
linked by selection; Enter advances to the next answer; the mouse wheel
scrolls and ctrl+wheel zooms about the pointer.

- [x] (9/2) Blank answers are warned about before a build and dropped from
the word bank, which also de-duplicates.

Stage 4 -- make building feel safe:

- [x] (9/2) Builds run on a worker thread with a modal progress dialog that
reports each file and can be cancelled. The window used to freeze with no
sign of life, so the natural response was to click Build again.

- [x] (9/2) The answer key is its own PDF by default, with an option to
combine. It used to be bound into the worksheet as page two of every
version, so printing thirty copies handed out the answers.

- [x] (9/2) Version N is reproducible: the shuffle is seeded from the
document rather than global random, the seed is saved in the .etqw file, and
each key page carries a short build code.

- [x] (9/2) Build failures are explained in a sentence naming the cause and
what to do -- a moved map image, a locked or unwritable folder, a full disk,
an unreadable image format -- instead of showing raw exception text.

- [x] (9/2) The running header shows the page number rather than a hardcoded
"of 2", which became a lie once a question list ran to a third page.

- [x] (9/2) Printed markers get the same white disc as the canvas and the
.etqw image, so a number no longer disappears against dark terrain.

- [ ] Stage 5 -- hand it to another teacher: marker dragging, wheel zoom and
panning, a menu bar, and a packaged double-clickable build.
