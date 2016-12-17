BUILT_SOURCES =
EXTRA_DIST =
CLEANFILES =
SUBDIRS = po

# ----------- trg --------------

trgdir = $(pythondir)/$(PACKAGE)/
trg_PYTHON = \
	$(wildcard trg/*.py)

bin_SCRIPTS = bin/transmission-remote-gnome
bin/transmission-remote-gnome: bin/transmission-remote-gnome.in Makefile
	@$(MKDIR_P) bin
	$(AM_V_GEN)$(SED)                       \
		-e s!\@pkgdatadir\@!$(pkgdatadir)!  \
		-e s!\@localedir\@!$(localedir)!    \
		-e s!\@pythondir\@!$(pythondir)!    \
		-e s!\@VERSION\@!$(VERSION)!        \
		-e s!\@PYTHON\@!$(PYTHON)!          \
		< $< > $@
	@chmod a+x $@

BUILT_SOURCES += bin/transmission-remote-gnome
EXTRA_DIST += bin/transmission-remote-gnome.in


app_id := se.tingping.Trg

gresource_xml := $(srcdir)/data/$(app_id).gresource.xml
gresource_data := $(app_id).gresource
noinst_DATA := $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir)/data --generate-dependencies $(gresource_xml))
pkgdata_DATA = $(gresource_data)
$(gresource_data): $(gresource_xml) $(noinst_DATA)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir)/data --generate $<
BUILT_SOURCES += $(gresource_data)

%.desktop: %.desktop.in
	@$(MKDIR_P) $$(dirname $@)
	$(AM_V_GEN)$(MSGFMT) --desktop --template $< -d $(srcdir)/po -o $@

desktop_in_files = data/$(app_id).desktop.in
desktop_FILES = $(desktop_in_files:.desktop.in=.desktop)
@DESKTOP_FILE_RULES@
EXTRA_DIST += $(desktop_in_files)
CLEANFILES += $(desktop_FILES)


%.appdata.xml: %.appdata.xml.in
	@$(MKDIR_P) $$(dirname $@)
	$(AM_V_GEN)$(MSGFMT) --xml --template $< -d $(srcdir)/po -o $@

appstream_in_files = data/$(app_id).appdata.xml.in
appstream_XML = $(appstream_in_files:.xml.in=.xml)
@APPSTREAM_XML_RULES@
EXTRA_DIST += $(appstream_in_files)
CLEANFILES += $(appstream_XML)


gsettings_SCHEMAS = data/$(app_id).gschema.xml
@GSETTINGS_RULES@

# This is just for running locally and not normally built
data/gschemas.compiled: $(gsettings_SCHEMAS)
	$(AM_V_GEN) $(GLIB_COMPILE_SCHEMAS) $(srcdir)/data --targetdir=$(builddir)/data

EXTRA_DIST += $(gsettings_SCHEMAS)
CLEANFILES += data/gschemas.compiled


run: $(BUILT_SOURCES) data/gschemas.compiled
	env GSETTINGS_SCHEMA_DIR=data SRCDIR=$(srcdir) bin/transmission-remote-gnome --log=3
