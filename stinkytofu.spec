# StinkyTofu — AMDGCN IR / assembler helpers for TensileLite rocisa (TheRock 10.1)

Name:		stinkytofu
Version:	10.1.0
Release:	1
%{!?rocm_llvm_maj_ver:%global rocm_llvm_maj_ver 23}
Summary:	AMDGCN IR toolkit for ROCm TensileLite / rocisa
License:	MIT
Group:		System/Libraries
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.1/stinkytofu.tar.gz#/stinkytofu-%{version}.tar.gz
# LLVM/libstdc++: UINT_MAX needs <climits>
# 10.1 already guards the monorepo ClangTidy include.
Patch0:		0002-climits-wmma.patch
# Monorepo default_amdclang.cmake is absent from the release tarball
Patch1:		0003-guard-default-amdclang.patch

BuildRequires:	rocm-rpm-macros
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	git-core
BuildRequires:	rocm-cmake
BuildRequires:	rocm-hip-devel
BuildRequires:	rocm-comgr-devel
BuildRequires:	clang >= %{rocm_llvm_maj_ver}
BuildRequires:	clang-tools
BuildRequires:	pkgconfig(libdrm)


%description
StinkyTofu is a C++ AMDGCN IR and assembler toolkit used by the rocisa
code generator (hipBLASLt TensileLite device library builds).

%package devel
Summary:	Development files for stinkytofu
Group:		Development/C++
Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	rocm-hip-devel
Requires:	rocm-comgr-devel
Provides:	cmake(stinkytofu) = %{version}

%description devel
Headers, CMake package, and conversion glue sources for rocisa.

%prep
%autosetup -n stinkytofu -p1

%build
export CC=clang
export CXX=clang++
export ROCM_PATH=%{_prefix}
export HIP_PATH=%{_prefix}
export HIP_DEVICE_LIB_PATH=%{_libdir}/amdgcn/bitcode
# Host-only tools (tablegen): keep --rocm-* out of CXXFLAGS (-Werror)
CXXFLAGS=$(printf '%s' "%{optflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CXXFLAGS
export CFLAGS="$CXXFLAGS"
export LDFLAGS=$(printf '%s' "%{?__global_ldflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')

%cmake %{rocm_cmake_fhs} \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_CXX_COMPILER=clang++ \
	-DBUILD_SHARED_LIBS=ON \
	-DSTINKYTOFU_ENABLE_WERROR=OFF \
	-DSTINKYTOFU_BUILD_TESTS=OFF \
	-DSTINKYTOFU_BUILD_EXAMPLES=OFF \
	-DSTINKYTOFU_BUILD_PYTHON=OFF \
	-DENABLE_CLANG_TIDY=OFF \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
# OM sets CMAKE_SKIP_RPATH=ON; tools need libstinkytofu while still in the build tree.
# The cmake macro leaves the shell in the build/ subdirectory.
export LD_LIBRARY_PATH="$(pwd)${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
%ninja_build

%install
cd build
DESTDIR=%{buildroot} /usr/bin/ninja install -j%{?_smp_build_ncpus}%{!?_smp_build_ncpus:8}
cd ..
# Upstream hardcodes DESTINATION lib (not lib64) and lib/cmake
if [ -d %{buildroot}/usr/lib ] && [ "%{_lib}" = "lib64" ]; then
	mkdir -p %{buildroot}%{_libdir}
	for f in %{buildroot}/usr/lib/libstinkytofu.so* %{buildroot}/usr/lib/intrinsics.st.bc; do
		[ -e "$f" ] || continue
		mv "$f" %{buildroot}%{_libdir}/
	done
	if [ -d %{buildroot}/usr/lib/cmake/stinkytofu ]; then
		mkdir -p %{buildroot}%{_libdir}/cmake
		mv %{buildroot}/usr/lib/cmake/stinkytofu %{buildroot}%{_libdir}/cmake/
		rmdir %{buildroot}/usr/lib/cmake 2>/dev/null || true
	fi
	# Generated export files still hardcode /lib/
	if [ -d %{buildroot}%{_libdir}/cmake/stinkytofu ]; then
		sed -i 's|/lib/libstinkytofu|/%{_lib}/libstinkytofu|g' \
			%{buildroot}%{_libdir}/cmake/stinkytofu/*
	fi
	rmdir %{buildroot}/usr/lib 2>/dev/null || true
fi
# Conversion glue sources are compiled into _rocisa (not libstinkytofu)
mkdir -p %{buildroot}%{_datadir}/stinkytofu/src/conversion/rocisa
install -m 644 src/conversion/rocisa/*.cpp \
	%{buildroot}%{_datadir}/stinkytofu/src/conversion/rocisa/

%files
%license LICENSE.md
%doc README.md
%{_libdir}/libstinkytofu.so.*
%{_libdir}/intrinsics.st.bc
%{_bindir}/stinkytofu-opt
%{_bindir}/stinkytofu-check
%{_bindir}/intrinsic-compiler

%files devel
%{_includedir}/stinkytofu/
%{_libdir}/libstinkytofu.so
%{_libdir}/cmake/stinkytofu/
%{_datadir}/stinkytofu/
