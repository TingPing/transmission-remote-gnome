conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(prefix, get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
conf.set('PYTHON', ' '.join(python.path()))
conf.set('pythondir', join_paths(prefix, pythondir))

configure_file(
  input: 'transmission-remote-gnome.in',
  output: 'transmission-remote-gnome',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

trg = join_paths(meson.build_root(), 'bin', 'transmission-remote-gnome')
run_target('run',
  command: [trg, '--log=3'],
  depends: [
#    trg_resources,
    trg_settings
  ]
)
