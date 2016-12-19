gnome = import('gnome')
app_id = 'se.tingping.Trg'

i18n.merge_file(
  input: app_id + '.desktop.in',
  output: app_id + '.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

i18n.merge_file(
  input: app_id + '.appdata.xml.in',
  output: app_id + '.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'appdata')
)

install_data(app_id + '.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

trg_resources = gnome.compile_resources(app_id,
  app_id + '.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir
)

trg_settings = gnome.compile_schemas()