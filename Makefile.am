# ----------- trg --------------

trgdir = $(pythondir)/$(PACKAGE)/
trg_PYTHON = \
	$(wildcard trg/*.py)

bin_SCRIPTS = bin/transmission-remote-gnome
bin/transmission-remote-gnome: bin/transmission-remote-gnome.in
	@$(MKDIR_P) bin
	$(AM_V_GEN)$(SED)                       \
		-e s!\@pkgdatadir\@!$(pkgdatadir)!  \
		-e s!\@localedir\@!$(localedir)!    \
		-e s!\@pythondir\@!$(pythondir)!    \
		-e s!\@VERSION\@!$(VERSION)!        \
		-e s!\@PYTHON\@!$(PYTHON)!          \
		< $< > $@
	@chmod a+x $@

# ----------- data --------------

noinst_DATA := $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir)/data --generate-dependencies $(srcdir)/data/trg.gresource.xml)
pkgdata_DATA = trg.gresource
trg.gresource: $(srcdir)/data/trg.gresource.xml $(noinst_DATA)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir)/data --generate $<

BUILT_SOURCES  = trg.gresource bin/transmission-remote-gnome
EXTRA_DIST = bin/transmission-remote-gnome.in

gsettings_SCHEMAS = data/io.github.Trg.gschema.xml
@GSETTINGS_RULES@

# This is just for running locally and not normally built
data/gschemas.compiled: $(gsettings_SCHEMAS)
	$(AM_V_GEN) $(GLIB_COMPILE_SCHEMAS) $(srcdir)/data --targetdir=$(builddir)/data

EXTRA_DIST += $(gsettings_SCHEMAS)
CLEANFILES = data/gschemas.compiled

run: $(BUILT_SOURCES) data/gschemas.compiled
	env GSETTINGS_SCHEMA_DIR=data SRCDIR=$(srcdir) bin/transmission-remote-gnome --log=3
