# TODO: proper gid, uid, etc.
Summary:	Fast, dense and secure container and virtual machine management
Name:		incus
Version:	7.0.0
Release:	0.1
License:	Apache v2.0
Group:		Applications/System
Source0:	https://github.com/lxc/incus/archive/v%{version}/%{name}-%{version}.tar.gz
# Source0-md5:	4f080d5ab0bd4c8022dbb796f97f31ff
Source1:	%{name}.service
Source2:	%{name}.init
Source3:	%{name}.sysconfig
Source4:	%{name}.sh
URL:		http://linuxcontainers.org/
BuildRequires:	acl-devel
BuildRequires:	cowsql-devel >= 1.15.9
%ifarch %{x8664} arm aarch64 ppc64
BuildRequires:	criu-devel >= 1.7
%endif
BuildRequires:	golang >= 1.23
BuildRequires:	libco-devel
BuildRequires:	libuv-devel
BuildRequires:	lxc-devel >= 6.0
BuildRequires:	pkgconfig
BuildRequires:	raft-devel >= 0.22.1
BuildRequires:	rpmbuild(macros) >= 1.228
BuildRequires:	udev-devel
Requires(post,preun):	/sbin/chkconfig
Requires(postun):	/usr/sbin/groupdel
Requires(pre):	/usr/bin/getgid
Requires(pre):	/usr/sbin/groupadd
Requires:	dnsmasq
Requires:	iproute2
Requires:	libcgroup
Requires:	lxc >= 6.0
Requires:	rc-scripts >= 0.4.0.10
Requires:	rsync
Requires:	squashfs
# for sqfs2tar
Requires:	squashfs-tools-ng
Requires:	tar
Requires:	uidmap
Requires:	uname(release) >= 4.1
Requires:	xz
Provides:	group(incus)
ExclusiveArch:	%{ix86} %{x8664} %{arm}
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%define		_enable_debug_packages 0
%define		gobuild(o:tags:) go build -ldflags "${GO_LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%define		goinstall go install -ldflags "${GO_LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v
%define		gopath		%{_libdir}/golang
%define		import_path	github.com/lxc/incus
%define		_libexecdir	%{_prefix}/lib

%description
incus is a next generation system container and virtual machine manager.

Specifically, it is made of three components:
- A system-wide daemon (incus)
- A command line client (lxc)
- An OpenStack Nova plugin (nova-compute-incus)

The daemon exports a REST API both locally and if enabled, over the
network.

The command line tool is designed to be a very simple, yet very
powerful tool to manage all your containers. It can handle connect to
multiple container hosts and easily give you an overview of all the
containers on your network, let you create some more where you want
them and even move them around while they are running.

The OpenStack plugin then allows you to use your incus hosts as compute
nodes, running workloads on containers rather than virtual machines.

%package agent
Summary:	incus Agent

%description agent
This package contains incus-agent program to be used inside virtual
machines (not containers) managed by incus.

%package tools
Summary:	incus Tools

%description tools
This package contains incus extra tools

%prep
%setup -q -n %{name}-%{version}

%build
export GOPATH=$(pwd)/_dist
export GOBIN=$GOPATH/bin
# flags from ArchLinux package
export CGO_LDFLAGS_ALLOW="-Wl,-z,now"

# linux agents
CGO_ENABLED=0 GO_LDFLAGS= %gobuild -o bin/ -tags=agent,netgo ./cmd/incus-agent/...

export GO_LDFLAGS="-compressdwarf=false -linkmode external"
export GOFLAGS="-buildmode=pie -modcacherw"
%gobuild -tags "netgo" -o bin/ ./cmd/incus-migrate/...
for tool in fuidshift incus lxc-to-incus lxd-to-incus incusd incus-benchmark incus-simplestreams incus-user; do
  %gobuild -tags "libsqlite3" -o bin/ ./cmd/$tool
done

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT{%{_bindir},%{_sbindir},%{_mandir}/man1,/etc/{rc.d/init.d,sysconfig},%{systemdunitdir}} \
	$RPM_BUILD_ROOT%{_libexecdir} \
	$RPM_BUILD_ROOT%{bash_compdir} \
	$RPM_BUILD_ROOT/var/lib/%{name}/{containers,devices,devincus,images,security,shmounts,snapshots} \
	$RPM_BUILD_ROOT/var/log/%{name}

install -d $RPM_BUILD_ROOT%{_libdir}/%{name}/rootfs

for tool in incus lxd-to-incus incus-migrate incus-user incusd; do
	install -p -Dm755 "bin/$tool" "$RPM_BUILD_ROOT%{_bindir}/$tool"
done

# VM Agents
for agent in bin/incus-agent*; do
	install -p -Dm755 "${agent}" "$RPM_BUILD_ROOT%{_libexecdir}/incus/agents/${agent##*/}"
done

# tools
for tool in fuidshift lxc-to-incus incus-benchmark incus-simplestreams; do
	install -p -Dm755 "bin/$tool" "$RPM_BUILD_ROOT%{_bindir}/$tool"
done

# shell completions
./bin/incus completion bash | install -Dm644 /dev/stdin "$RPM_BUILD_ROOT/usr/share/bash-completion/completions/incus"
./bin/incus completion zsh | install -Dm644 /dev/stdin "$RPM_BUILD_ROOT/usr/share/zsh/site-functions/_incus"
./bin/incus completion fish | install -Dm644 /dev/stdin "$RPM_BUILD_ROOT/usr/share/fish/vendor_completions.d/incus.fish"

cp -p %{SOURCE1} $RPM_BUILD_ROOT%{systemdunitdir}
install -p %{SOURCE2} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}
cp -p %{SOURCE3} $RPM_BUILD_ROOT/etc/sysconfig/%{name}

install -p %{SOURCE4} $RPM_BUILD_ROOT%{_libexecdir}/incus-wrapper

%pre
%groupadd -g 273 %{name}

%post
/sbin/chkconfig --add %{name}
%service -n %{name} restart
%systemd_post %{name}.service


%preun
if [ "$1" = "0" ]; then
	%service -q %{name} stop
	/sbin/chkconfig --del %{name}
fi
%systemd_preun %{name}.service

%postun
if [ "$1" = "0" ]; then
	%groupremove %{name}
fi
%systemd_reload

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%doc AUTHORS doc/*
%config(noreplace) %verify(not md5 mtime size) /etc/sysconfig/%{name}
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%attr(755,root,root) %{_bindir}/incus
%attr(755,root,root) %{_bindir}/incusd
%attr(755,root,root) %{_bindir}/incus-simplestreams
%attr(755,root,root) %{_bindir}/incus-user
%{systemdunitdir}/%{name}.service
%dir %attr(750,root,root) %{_libdir}/%{name}
%dir %attr(750,root,root) %{_libdir}/%{name}/rootfs
%attr(750,root,root) %{_libexecdir}/%{name}-wrapper
%dir %attr(750,root,logs) /var/log/%{name}
%dir %attr(711,root,incus) /var/lib/%{name}
%dir %attr(711,root,root) /var/lib/%{name}/containers
%dir %attr(700,root,root) /var/lib/%{name}/devices
%dir %attr(700,root,root) /var/lib/%{name}/devincus
%dir %attr(700,root,root) /var/lib/%{name}/images
%dir %attr(700,root,root) /var/lib/%{name}/security
%dir %attr(711,root,root) /var/lib/%{name}/shmounts
%dir %attr(700,root,root) /var/lib/%{name}/snapshots
%{bash_compdir}/incus

%files agent
%defattr(644,root,root,755)
%attr(755,root,root) %{_libexecdir}/incus/agents/incus-agent*

%files tools
%defattr(644,root,root,755)
%attr(755,root,root) %{_bindir}/fuidshift
%attr(755,root,root) %{_bindir}/lxc-to-incus
%attr(755,root,root) %{_bindir}/lxd-to-incus
%attr(755,root,root) %{_bindir}/incus-benchmark
%attr(755,root,root) %{_bindir}/incus-migrate
