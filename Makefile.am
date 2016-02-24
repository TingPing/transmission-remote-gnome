# ----------- trg --------------

trgdir = $(pythondir)/$(PACKAGE)/
trg_PYTHON = \
	$(wildcard trg/*.py)

trg/__main__.py: trg/__main__.py.in
	$(AM_V_GEN)sed                          \
		-e s!\@pkgdatadir\@!$(pkgdatadir)!  \
		-e s!\@localedir\@!$(localedir)!    \
		-e s!\@pythondir\@!$(pythondir)!    \
		-e s!\@VERSION\@!$(VERSION)!        \
		-e s!\@PYTHON\@!$(PYTHON)!          \
		< $< > $@

run: $(BUILT_SOURCES) data/gschemas.compiled
	env GSETTINGS_SCHEMA_DIR=data $(PYTHON) -m trg --log=3

# ----------- data --------------

noinst_DATA = $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=data --generate-dependencies data/trg.gresource.xml)
pkgdata_DATA = trg.gresource
trg.gresource: data/trg.gresource.xml $(noinst_DATA)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(top_srcdir)/data --generate $<

BUILT_SOURCES  = trg.gresource trg/__main__.py
EXTRA_DIST = trg/__main__.py.in

gsettings_SCHEMAS = data/io.github.Trg.gschema.xml
@GSETTINGS_RULES@

# This is just for running locally and not normally built
data/gschemas.compiled: $(gsettings_SCHEMAS)
	$(AM_V_GEN) $(GLIB_COMPILE_SCHEMAS) data

EXTRA_DIST += $(gsettings_SCHEMAS)
CLEANFILES = data/gschemas.compiled

