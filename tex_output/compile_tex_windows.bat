@echo off
for %%f in (*.tex) do (
    pdflatex %%f
)
pause
