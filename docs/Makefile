# Makefile for Sphinx documentation

# If `python3` doesn't point to the Python you want to use (with Sphinx installed),
# then you can use, e.g., `make html PYTHON=python3.9` to specify a Python executable
PYTHON = python3

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = LANG=C $(PYTHON) -msphinx

FILES=

# Internal variables.
ALLSPHINXOPTS   = -d build/doctrees $(SPHINXOPTS) source

.PHONY: help clean html changes linkcheck dist version-check

#------------------------------------------------------------------------------

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html      to make standalone HTML files"
	@echo "  pickle    to make pickle files (usable by e.g. sphinx-web)"
	@echo "  htmlhelp  to make HTML files and a HTML help project"
	@echo "  changes   to make an overview over all changed/added/deprecated items"
	@echo "  linkcheck to check all external links for integrity"
	@echo "  clean     to clean all build files/directories"
	@echo "  dist      to make a distribution-ready tree (installing Scipy in venv)"
	@echo "  doc-dist  to make a distribution-ready tree (assuming Scipy is installed)"
	@echo "  show      to show the HTML output"

clean:
	-rm -rf build/* source/reference/generated


#------------------------------------------------------------------------------
# Automated generation of all documents
#------------------------------------------------------------------------------

# Build the current scipy version, and extract docs from it.
# We have to be careful of some issues:
#
# - Everything must be done using the same Python version
# - We must use eggs (otherwise they might override PYTHONPATH on import).
# - Different versions of easy_install install to different directories (!)
#

OPENTPSVER:=$(shell cd '..' ; $(PYTHON) -c "import version; print(version.git_revision[:10])" 2>/dev/null)
GITVER ?= $(shell cd tools; $(PYTHON) -c "from version_utils import git_version; \
				print(git_version('..')[0][:10])")

version-check:
ifeq "$(GITVER)" "Unknown"
	# @echo sdist build with unlabeled sources
else ifeq ("", "$(OPENTPSVER)")
	@echo opentps not found, cannot build documentation without successful \"import opentps\"
	@exit 1
else ifneq ($(OPENTPSVER),$(GITVER))
	@echo installed opentps $(OPENTPSVER) != current repo git version \'$(GITVER)\'
	@echo use '"make dist"' or '"GITVER=$(OPENTPSVER) make $(MAKECMDGOALS) ..."'
	@exit 1
else
	# for testing
	# @echo installed opentps $(OPENTPSVER) matches git version $(GITVER); exit 1
endif

dist:
	install -d build
	rm -rf build/env
	$(PYTHON) -mvenv --system-site-packages build/env
	$(CURDIR)/build/env/bin/python -mpip install -r ../doc_requirements.txt
	$(CURDIR)/build/env/bin/python -mpip install ..
	make PYTHON="$(CURDIR)/build/env/bin/python" doc-dist

doc-dist: VERSIONWARNING=-t versionwarning

doc-dist: html
	-test -d build/htmlhelp || make htmlhelp-build
	-rm -rf build/dist
	mkdir -p build/dist
	cp -r build/html/* build/dist
	(cd build/html && zip -9qr ../dist/scipy-html.zip .)
	chmod ug=rwX,o=rX -R build/dist
	find build/dist -type d -print0 | xargs -0r chmod g+s
	cd build/dist && tar czf ../dist.tar.gz *

#------------------------------------------------------------------------------
# Basic Sphinx generation rules for different formats
#------------------------------------------------------------------------------

html: version-check html-build
html-build:
	mkdir -p build/html build/doctrees
	$(SPHINXBUILD) -WT --keep-going $(VERSIONWARNING) -b html $(ALLSPHINXOPTS) build/html $(FILES)

coverage: build version-check
	mkdir -p build/coverage build/doctrees
	$(SPHINXBUILD) -b coverage $(ALLSPHINXOPTS) build/coverage $(FILES)
	@echo "Coverage finished; see c.txt and python.txt in build/coverage"

changes: version-check
	mkdir -p build/changes build/doctrees
	$(SPHINXBUILD) -b changes $(ALLSPHINXOPTS) build/changes $(FILES)
	@echo
	@echo "The overview file is in build/changes."

linkcheck: version-check
	mkdir -p build/linkcheck build/doctrees
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) build/linkcheck $(FILES)
	@echo
	@echo "Link check complete; look for any errors in the above output " \
	      "or in build/linkcheck/output.txt."

show:
	@python -c "import webbrowser; webbrowser.open_new_tab('file://$(PWD)/build/html/index.html')"
