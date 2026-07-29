TODOs for MapQuizMaker
======================

- [ ] (7/29) Needs refactoring to use Pathlib.

- [ ] (7/29) I want to significantly simplify the files that make up the app.
I want to lean on uv for package management, etc, and bring the file names and
duties into line with standard Python best-practices.

- [ ] (7/29) I don't particularly like the basic Tkinter look. Advise on 
tkinter styling templates that might be nice to look at.

- [ ] (7/29) I don't like the terminal output tracking the GUI. People who use 
the GUI are going to be weirded out by it.

- [ ] (7/29) The Class, Title, Version, and Instruction fields are very poorly 
laid out. I think I was going for the most basic, easiest-to-implement layout,
but it looks not very professional.

- [ ] (7/29) The Instructions field should really be a paragraph, not just a
small field that looks like it would take a single word.

- [ ] (7/29) I've been moving my typesetting workflow to Typst as much as possible.
If it is possible to accomplish the same thing with Typst as I have here with
LaTeX, I want to refactor to use Typst instead. That way, I can bundle the Typst
Python library with it and using the app won't require a massive LaTeX install.

- [ ] (7/29) The app should automatically compile the output it creates (ideally
with Typst).

- [ ] (7/29) There should be an option to automatically save n versions of the 
quiz with automatic version numbering. There should be an option (default 
unselected) to save each as a separate file.

- [ ] (7/29) When the user deletes one of the locations on the map, the rest of
the numbers should reorder. There's no reason for any particular order since 
the numbers are going to change on the quizzes anyway.

- [ ] (7/29) There should be an option to print a word-bank at the beginning of
the questions section after the image.

