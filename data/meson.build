gnome = import('gnome')
app_id = 'se.tingping.Trg'

desktop_conf = configuration_data()
desktop_conf.set('bindir', join_paths(prefix, get_option('bindir')))

desktop_file = configure_file(
  input: app_id + '.desktop.in.in',
  output: app_id + '.desktop.in',
  configuration: desktop_conf
)

# TODO: Requires GLib 2.52 because of Meson issue
#desktop_service = configure_file(
#  input: app_id + '.service.desktop.in',
#  output: app_id + '.service.desktop',
#  configuration: desktop_conf,
#  install: true,
#  install_dir: pkgdatadir,
#)

trg_desktop = i18n.merge_file(
  input: desktop_file,
  output: app_id + '.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

trg_appstream = i18n.merge_file(
  input: app_id + '.appdata.xml.in',
  output: app_id + '.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'appdata')
)

dbus_conf = configuration_data()
dbus_conf.set('bindir', join_paths(prefix, get_option('bindir')))

configure_file(
  input: app_id + '.service.in',
  output: app_id + '.service',
  configuration: dbus_conf,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'dbus-1/services')
)

install_data(app_id + '.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

if false
gtk_encode_symbolic = find_program('gtk-encode-symbolic-svg')
sizes = ['32x32', '64x64']
icon_targets = []
foreach size: sizes
  icon_targets += custom_target('symbolic-icon-' + size,
    input: 'icons/turtle-symbolic.svg',
    output: 'turtle-symbolic.symbolic.png',
    command: [gtk_encode_symbolic, '--output=' + meson.current_build_dir(), '@INPUT@', size]
  )
endforeach
endif

icondir = join_paths(get_option('datadir'), 'icons/hicolor')
install_data('icons/se.tingping.Trg.svg',
  install_dir: join_paths(icondir, 'scalable/apps')
)
install_data('icons/se.tingping.Trg-symbolic.svg',
  install_dir: join_paths(icondir, 'symbolic/apps')
)

trg_resources = gnome.compile_resources(app_id,
  app_id + '.gresource.xml',
  gresource_bundle: true,
  # dependencies: desktop_service,
  install: true,
  install_dir: pkgdatadir
)

trg_settings = gnome.compile_schemas()

# ---- Tests ----

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate-relax', trg_appstream]
  )
endif

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [trg_desktop]
  )
endif

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif
