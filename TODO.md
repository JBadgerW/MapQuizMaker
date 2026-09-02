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

- [ ] Stage 2 -- make it installable: template and fonts inside the package,
loaded via importlib.resources and shipped in the wheel. An installed copy
currently cannot build at all.

- [ ] Stage 3 -- give it a document: normalized marker coordinates, one
authoritative state object with reconciling views, and a .mapquiz project
file with New / Open / Save / Recent, a dirty flag, and undo.

- [ ] Stage 4 -- make building feel safe: worker-thread builds with a
progress dialog, separate answer-key PDF by default, friendly error
messages, and seeded reproducible versions.

- [ ] Stage 5 -- hand it to another teacher: marker dragging, wheel zoom and
panning, a menu bar, and a packaged double-clickable build.
