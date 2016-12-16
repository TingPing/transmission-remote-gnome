AC_PREREQ(2.68)
AC_INIT([trg], [0.1.0])
AC_CONFIG_AUX_DIR([build-aux])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([trg/application.py])
AC_CONFIG_FILES([Makefile])

AM_INIT_AUTOMAKE([1.11 dist-xz no-dist-gzip foreign subdir-objects -Wall -Wno-portability])
AM_SILENT_RULES([yes])
AM_PATH_PYTHON([3.3])

AC_PROG_SED
AC_PATH_PROG(GLIB_COMPILE_RESOURCES, glib-compile-resources)
AX_REQUIRE_DEFINED([GLIB_GSETTINGS])
GLIB_GSETTINGS

AC_OUTPUT
echo "
    $PACKAGE $VERSION

    prefix:         ${prefix}
"
