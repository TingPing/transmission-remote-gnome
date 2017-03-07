%global appid se.tingping.Trg

Name:    transmission-remote-gnome
Version: 0.1.0
Release: 1%{dist}
Summary: Remote client for Transmission
License: GPLv3+
URL:     https://github.com/TingPing/transmission-remote-gnome
Source0: %{name}-%{version}.tar.gz

BuildArch: noarch
BuildRequires: python3-devel >= 3.4
BuildRequires: meson >= 0.37.0
BuildRequires: pkgconfig(glib-2.0)
BuildRequires: libappstream-glib
BuildRequires: gettext
Requires: python3-gobject
Requires: gtk3 >= 3.20
Requires: libsoup

%description
Remote client to connect to the Transmission daemon allowing you to manage torrents and settings.

%prep
%autosetup -p1

%build
%meson
%meson_build

%install
%meson_install
#%find_lang trg

%check
/usr/bin/appstream-util validate-relax --nonet %{buildroot}/%{_datadir}/appdata/*.appdata.xml

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

# -f trg.lang
%files
%license COPYING
%doc README.md
%{_bindir}/transmission-remote-gnome
%dir %{python3_sitelib}/trg
%{python3_sitelib}/trg/
%{_datadir}/trg/%{appid}.gresource
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/dbus-1/services/%{appid}.service
%{_datadir}/appdata/%{appid}.appdata.xml
%{_datadir}/glib-2.0/schemas/%{appid}.gschema.xml
%{_datadir}/icons/hicolor/**/apps/%{appid}*.svg
