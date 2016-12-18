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

meson.add_install_script('meson_post_install.py')

