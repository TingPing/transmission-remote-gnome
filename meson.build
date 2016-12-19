project('trg', 'c',
  version: '0.1.0',
  meson_version: '>= 0.37.0'
)

i18n = import('i18n')
prefix = get_option('prefix')
pkgdatadir = join_paths(prefix, get_option('datadir'), meson.project_name())
python = find_program('python3')

# Get the relative path without the prefix
get_purelib_script = '''
print(__import__("sysconfig").get_path("purelib", vars={"base":""})[1:])
'''
ret = run_command(python, ['-c', get_purelib_script])
if ret.returncode() != 0
  error('Failed to determine python lib directory')
else
  pythondir = ret.stdout().strip()
  message('Found python dir: ' + pythondir)
endif

install_subdir('trg', install_dir: pythondir)
subdir('data')
subdir('bin')
subdir('po')

meson.add_install_script('scripts/meson_post_install.py')

if find_program('flatpak-builder', required: false).found()
  # We keep a generic manifest in the repo you can use but
  # we want builds to use the local files so simply rewrite it
  make_local_manifest = find_program('scripts/make_local_manifest.py')
  local_manifest = custom_target('manifest',
    input: 'se.tingping.Trg.json',
    output: 'se.tingping.Trg.json',
    command: [make_local_manifest, '@INPUT@', '@OUTPUT@']
  )

  # Build a bundle for both testing and releases
  build_flatpak = find_program('scripts/build_flatpak.py')
  custom_target('flatpak',
    input: local_manifest,
    output: 'se.tingping.Trg.flatpak',
    command: [build_flatpak, '@INPUT@', '@OUTPUT@'],
    build_always: true
  )
endif
