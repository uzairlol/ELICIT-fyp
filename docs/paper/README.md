# Compiling the manuscript

From this directory (requires a TeX engine with Times New Roman / TeX Gyre Termes):

```bash
# With tectonic (bundled under .tools/ if downloaded):
./.tools/tectonic.exe -X compile main.tex

# Or with a standard TeX Live / MiKTeX install:
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

On Windows with XeLaTeX/LuaLaTeX, Times New Roman is loaded via `fontspec`.
With pdfLaTeX, `mathptmx` provides a Times-compatible face.

Output: `main.pdf`
