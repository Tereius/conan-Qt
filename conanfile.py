#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment
from conans.errors import ConanException
from distutils.spawn import find_executable
import os
import shutil
import configparser
import re
import stat


class QtConan(ConanFile):

    def getsubmodules():
        config = configparser.ConfigParser()
        config.read('qtmodules.conf')
        res = {}
        assert config.sections()
        for s in config.sections():
            section = str(s)
            assert section.startswith("submodule ")
            assert section.count('"') == 2
            modulename = section[section.find('"') + 1 : section.rfind('"')]
            status = str(config.get(section, "status"))
            if status != "obsolete" and status != "ignore":
                res[modulename] = {"branch":str(config.get(section, "branch")), "status":status, "path":str(config.get(section, "path"))}
                if config.has_option(section, "depends"):
                    res[modulename]["depends"] = [str(i) for i in config.get(section, "depends").split()]
                else:
                    res[modulename]["depends"] = []
        return res
    submodules = getsubmodules()

    name = "Qt"
    version = "5.12.10"
    description = "Conan.io package for Qt library."
    url = "https://github.com/Tereius/conan-Qt"
    homepage = "https://www.qt.io/"
    license = "http://doc.qt.io/qt-5/lgpl.html"
    exports = ["LICENSE.md", "qtmodules.conf"]
    exports_sources = ["CMakeLists.txt", "fix_qqmlthread_assertion_dbg.diff"]
    settings = "os", "arch", "compiler", "build_type"

    options = dict({
        "shared": [True, False],
        "fPIC": [True, False],
        "opengl": ["no", "es2", "desktop", "dynamic"],
        "openssl": [True, False],
        "GUI": [True, False],
        "widgets": [True, False],
        "config": "ANY",
        }, **{module: [True,False] for module in submodules}
    )
    no_copy_source = True
    default_options = ("shared=True", "fPIC=True", "opengl=desktop", "openssl=False", "GUI=True", "widgets=True", "config=None") + tuple(module + "=False" for module in submodules)
    short_paths = True

    def build_requirements(self):
        self._build_system_requirements()
        if self.settings.os == 'Emscripten':
            self.build_requires("emsdk_installer/1.38.29@bincrafters/stable")
        if self.settings.os == 'Windows' and self.settings.compiler == 'Visual Studio':
            self.build_requires("jom/1.1.3")

    def configure(self):
        if self.settings.os == "iOS":
            raise ConanException("iOS not supported")
        if self.options.openssl:
            self.requires("openssl/1.1.1i")
            if self.settings.os == 'Emscripten':
                self.options["openssl"].shared = False
            else:
                self.options["openssl"].shared = True
        if self.options.widgets == True:
            self.options.GUI = True
        if not self.options.GUI:
            self.options.opengl = "no"
        if self.settings.os == "Android":
            if self.options.opengl != "no":
                self.options.opengl = "es2"
        if self.settings.os == 'Emscripten':
            self.options.shared = False
            if self.options.opengl != "no":
                self.options.opengl = "es2"

        assert QtConan.version == QtConan.submodules['qtbase']['branch']
        def enablemodule(self, module):
            setattr(self.options, module, True)
            for req in QtConan.submodules[module]["depends"]:
                enablemodule(self, req)
        self.options.qtbase = True
        for module in QtConan.submodules:
            if getattr(self.options, module):
                enablemodule(self, module)

    def _build_system_requirements(self):
        if self.settings.os == "Linux" and tools.os_info.is_linux:
            installer = tools.SystemPackageTool()
            if tools.os_info.with_apt:
                pack_names = []
                arch_suffix = ''
                if self.settings.arch == "x86":
                    arch_suffix = ':i386'
                elif self.settings.arch == "x86_64":
                    arch_suffix = ':amd64'
                if self.options.GUI:
                    pack_names.extend(["libxcb1-dev", "libx11-dev", "libfontconfig1-dev", "libfreetype6-dev", "libxext-dev", "libxfixes-dev", "libxi-dev", "libxrender-dev", "libx11-xcb-dev", "libxcb-glx0-dev", "libxkbcommon-dev"])
                    if self.options.opengl == "desktop":
                        pack_names.append("libgl1-mesa-dev")
                if self.options.qtmultimedia:
                    pack_names.extend(["libasound2-dev", "libpulse-dev", "libgstreamer1.0-dev", "libgstreamer-plugins-base1.0-dev"])
                if self.options.qtwebengine:
                    pack_names.extend(["libssl-dev", "libxcursor-dev", "libxcomposite-dev", "libxdamage-dev", "libxrandr-dev", "libdbus-1-dev", "libfontconfig1-dev", "libcap-dev", "libxtst-dev", "libpulse-dev", "libudev-dev", "libpci-dev", "libnss3-dev", "libasound2-dev", "libxss-dev", "libegl1-mesa-dev", "gperf", "bison"])       
                for package in pack_names:
                    installer.install(package + arch_suffix)
            elif tools.os_info.with_yum:
                pack_names = []
                arch_suffix = ''
                if self.settings.arch == "x86":
                    arch_suffix = '.i686'
                elif self.settings.arch == "x86_64":
                    arch_suffix = '.x86_64'
                if self.options.GUI:
                    pack_names.extend(["libxcb-devel", "libX11-devel", "fontconfig-devel", "freetype-devel", "libXext-devel", "libXfixes-devel", "libXi-devel", "libXrender-devel", "libxkbcommon-devel"])
                    if self.options.opengl == "desktop":
                        pack_names.append("mesa-libGL-devel")
                if self.options.qtmultimedia:
                    pack_names.extend(["alsa-lib-devel", "pulseaudio-libs-devel", "gstreamer-devel", "gstreamer-plugins-base-devel"])
                if self.options.qtwebengine:
                    pack_names.extend(["libgcrypt-devel", "libgcrypt", "pciutils-devel", "nss-devel", "libXtst-devel", "gperf", "cups-devel", "pulseaudio-libs-devel", "libgudev1-devel", "systemd-devel", "libcap-devel", "alsa-lib-devel", "flex", "bison", "libXrandr-devel", "libXcomposite-devel", "libXcursor-devel", "fontconfig-devel"])
                for package in pack_names:
                    installer.install(package + arch_suffix)
            else:
                self.output.warn("Couldn't install system requirements")

    def source(self):
        url = "http://download.qt.io/official_releases/qt/{0}/{1}/single/qt-everywhere-src-{1}"\
            .format(self.version[:self.version.rfind('.')], self.version)
        if tools.os_info.is_windows:
            tools.get("%s.zip" % url)
        else:
            tools.get("%s.tar.xz" % url)
            #self.run("wget -qO- %s.tar.xz | tar -xJ " % url)
        shutil.move("qt-everywhere-src-%s" % self.version, "qt5")

        # patches
        #tools.replace_in_file("qt5/qtbase/src/plugins/platforms/ios/qioseventdispatcher.mm", "namespace", "Q_LOGGING_CATEGORY(lcEventDispatcher, \"qt.eventdispatcher\"); \n namespace")
        #tools.replace_in_file("qt5/qtdeclarative/tools/qmltime/qmltime.pro", "QT += quick-private", "QT += quick-private\nios{\nCONFIG -= bitcode\n}")
        #tools.replace_in_file("qt5/qtbase/src/platformsupport/clipboard/clipboard.pro", "macos: LIBS_PRIVATE += -framework AppKit", "macos: LIBS_PRIVATE += -framework AppKit\nios {\nLIBS += -framework MobileCoreServices\n}")

        #tools.replace_in_file("qt5/qtbase/src/corelib/tools/qsimd_p.h", "#    include <x86intrin.h>", "# if !defined(__EMSCRIPTEN__)\n#  include <x86intrin.h>\n# endif")

        # Do not use subdirectories in plugin folder since this is not App Store compatible
        tools.replace_in_file("qt5/qtdeclarative/src/3rdparty/masm/wtf/OSAllocatorPosix.cpp", "#include <sys/syscall.h>", "#include <sys/syscall.h>\n#include <linux/limits.h>")
        
        tools.replace_in_file("qt5/qtlocation/src/3rdparty/mapbox-gl-native/platform/default/bidi.cpp", "#include <memory>", "#include <memory>\n#include <stdexcept>")
        
        tools.replace_in_file("qt5/qtlocation/src/3rdparty/mapbox-gl-native/src/mbgl/util/convert.cpp", "#include <mbgl/util/convert.hpp>", "#include <mbgl/util/convert.hpp>\n#include <stdint.h>")

        # fix error with mersenne_twisters
        # https://codereview.qt-project.org/c/qt/qtbase/+/245425
        # should not needed in Qt >= 5.12.1
        tools.patch(patch_file="fix_qqmlthread_assertion_dbg.diff", base_path="qt5/qtdeclarative/")

    def _toUnixPath(self, paths):
        if self.settings.os == "Android" and tools.os_info.is_windows:
            if(isinstance(paths, list)):
                return list(map(lambda x: tools.unix_path(x), paths))
            else:
                return tools.unix_path(paths)
        else:
            return paths

    def build(self):
        args = ["-v", "-opensource", "-confirm-license", "-nomake examples", "-nomake tests",
                "-extprefix %s" % self._toUnixPath(self.package_folder)]
        if not self.options.GUI:
            args.append("-no-gui")
        if not self.options.widgets:
            args.append("-no-widgets")
        if not self.options.shared:
            args.insert(0, "-static")
            if self.settings.os == "Windows":
                if self.settings.compiler.runtime == "MT" or self.settings.compiler.runtime == "MTd":
                    args.append("-static-runtime")
        else:
            args.insert(0, "-shared")
        if self.settings.build_type == "Debug":
            args.append("-debug")
        else:
            args.append("-release")
        for module in QtConan.submodules:
            if not getattr(self.options, module) and os.path.isdir(os.path.join(self.source_folder, 'qt5', QtConan.submodules[module]['path'])):
                args.append("-skip " + module)

        # openGL
        if self.options.opengl == "no":
            args += ["-no-opengl"]
        elif self.options.opengl == "es2":
            args += ["-opengl es2"]
        elif self.options.opengl == "desktop":
            args += ["-opengl desktop"]
        if self.settings.os == "Windows":
            if self.options.opengl == "dynamic":
                args += ["-opengl dynamic"]

        # openSSL
        if not self.options.openssl:
            args += ["-no-openssl"]
        else:
            args += ["-openssl-linked"]
            args += ["-I %s" % i for i in self._toUnixPath(self.deps_cpp_info["openssl"].include_paths)]
            libs = self._toUnixPath(self.deps_cpp_info["openssl"].libs)
            lib_paths = self._toUnixPath(self.deps_cpp_info["openssl"].lib_paths)
            os.environ["OPENSSL_LIBS"] = " ".join(["-L"+i for i in lib_paths] + ["-l"+i for i in libs])
            os.environ["OPENSSL_LIBS_DEBUG"] = " ".join(["-L"+i for i in lib_paths] + ["-l"+i for i in libs])
            os.environ["LD_RUN_PATH"] = " ".join([i+":" for i in lib_paths]) # Needed for secondary (indirect) dependency resolving of gnu ld
            os.environ["LD_LIBRARY_PATH"] = " ".join([i+":" for i in lib_paths]) # Needed for secondary (indirect) dependency resolving of gnu ld

        if self.options.config:
            args.append(str(self.options.config))

        if self.settings.os == "Windows":
            if self.settings.compiler == "Visual Studio":
                self._build_msvc(args)
            else:
                self._build_mingw(args)
        elif self.settings.os == "Android":
            self._build_android(args)
        elif self.settings.os == "Emscripten":
            self._build_wasm(args)
        elif self.settings.os == "Linux" and os.getenv("RASPBIAN_ROOTFS") is not None:
            self._build_raspbian(args)
        else:
            self._build_unix(args)

        with open('qtbase/bin/qt.conf', 'w') as f:
            f.write('[Paths]\nPrefix = ..')

    def _build_msvc(self, args):
        build_command = find_executable("jom.exe")
        if build_command:
            build_args = ["-j", str(tools.cpu_count())]
        else:
            build_command = "nmake.exe"
            build_args = []
        self.output.info("Using '%s %s' to build" % (build_command, " ".join(build_args)))


        with tools.vcvars(self.settings):
            self.run("%s/qt5/configure %s" % (self.source_folder, " ".join(args)))
            self.run("%s %s" % (build_command, " ".join(build_args)))
            self.run("%s install" % build_command)

    def _build_mingw(self, args):
        # Workaround for configure using clang first if in the path
        new_path = []
        for item in os.environ['PATH'].split(';'):
            if item != 'C:\\Program Files\\LLVM\\bin':
                new_path.append(item)
        os.environ['PATH'] = ';'.join(new_path)
        # end workaround
        args += ["-xplatform win32-g++"]

        with tools.environment_append({"MAKEFLAGS":"-j %d" % tools.cpu_count()}):
            self.output.info("Using '%d' threads" % tools.cpu_count())
            self.run("%s/qt5/configure.bat %s" % (self.source_folder, " ".join(args)))
            self.run("mingw32-make")
            self.run("mingw32-make install")

    def _build_unix(self, args):
        if self.settings.os == "Linux":
            args.append("-no-use-gold-linker") # QTBUG-65071
            if self.options.GUI:
                args.append("-qt-xcb")
            if self.settings.arch == "x86":
                args += ["-xplatform linux-g++-32"]
            elif self.settings.arch == "armv6":
                args += ["-xplatform linux-arm-gnueabi-g++"]
            elif self.settings.arch == "armv7":
                args += ["-xplatform linux-arm-gnueabi-g++"]
        else:
            args += ["-no-framework"]
            if self.settings.arch == "x86":
                args += ["-xplatform macx-clang-32"]

        env_build = AutoToolsBuildEnvironment(self)
        self.run("%s/qt5/configure %s" % (self.source_folder, " ".join(args)))
        env_build.make()
        env_build.install()

    def _build_android(self, args):
        # end workaround
        args += ["--disable-rpath", "-skip qtserialport"]
        if tools.os_info.is_windows:
            args += ["-platform win32-g++"]
        
        if self.settings.compiler == 'gcc':
            args += ["-xplatform android-g++"]
        else:
            args += ["-xplatform android-clang"]
        args += ["-android-ndk-platform android-%s" % (str(self.settings.os.api_level))]
        args += ["-android-ndk " + self._toUnixPath(self.deps_env_info['android-ndk'].NDK_ROOT)]
        args += ["-android-sdk " + self._toUnixPath(self.deps_env_info['android-sdk'].SDK_ROOT)]
        args += ["-android-ndk-host %s-%s" % (str(self.settings_build.os).lower(), str(self.settings_build.arch))]
        #args += ["-android-toolchain-version " + self.deps_env_info['android-ndk'].TOOLCHAIN_VERSION]
        #args += ["-sysroot " + tools.unix_path(self.deps_env_info['android-ndk'].SYSROOT)]
        args += ["-device-option CROSS_COMPILE=" + self.deps_env_info['android-ndk'].CHOST + "-"]

        if str(self.settings.arch).startswith('x86_64'):
            args.append('-android-arch x86_64')
        elif str(self.settings.arch).startswith('x86'):
            args.append('-android-arch x86')
        elif str(self.settings.arch).startswith('armv6'):
            args.append('-android-arch armeabi')
        elif str(self.settings.arch).startswith('armv7'):
            args.append("-android-arch armeabi-v7a")
        elif str(self.settings.arch).startswith('armv8'):
            args.append("-android-arch arm64-v8a")

        self.output.info("Using '%d' threads" % tools.cpu_count())
        with tools.environment_append({
                # The env. vars set by conan android-ndk. Configure doesn't read them (on windows they contain backslashes).
                "NDK_ROOT": self._toUnixPath(tools.get_env("NDK_ROOT")),
                "ANDROID_NDK_ROOT": self._toUnixPath(tools.get_env("NDK_ROOT")),
                "SYSROOT": self._toUnixPath(tools.get_env("SYSROOT")),
                "MAKEFLAGS":"-j %d" % tools.cpu_count()
            }):
            self.run(self._toUnixPath("%s/qt5/configure " % self.source_folder) + " ".join(args), win_bash=tools.os_info.is_windows, msys_mingw=tools.os_info.is_windows)
            self.run("make", win_bash=tools.os_info.is_windows)
            self.run("make install", win_bash=tools.os_info.is_windows)

    def _build_wasm(self, args):
        args += ["--disable-rpath", "-skip qttranslations", "-skip qtserialport"]
        args += ["-xplatform wasm-emscripten"]
        env_build = AutoToolsBuildEnvironment(self)
        self.run("%s/qt5/configure %s" % (self.source_folder, " ".join(args)))
        env_build.make()
        env_build.install()

    def _build_raspbian(self, args):
        args += ["--disable-rpath", "-skip qttranslations", "-skip qtserialport"]
        args += ["-device linux-rasp-pi-g++"]
        args += ["-device-option CROSS_COMPILE=" + self.deps_env_info['raspbian'].CHOST + "-"]
        args += ["-sysroot " + self.deps_env_info['raspbian'].RASPBIAN_ROOTFS]
        env_build = AutoToolsBuildEnvironment(self)
        self.run("%s/qt5/configure %s" % (self.source_folder, " ".join(args)))
        env_build.make()
        env_build.install()

    def package(self):
        self.copy("bin/qt.conf", src="qtbase")
        if self.settings.os == "Android":
            # One qt cmake file contains hardcoded paths. We have to remove those. Otherwise this arifact wouldn't be relocatable
            file_name = os.path.join(self.package_folder, "lib", "cmake", "Qt5Gui", "Qt5GuiConfigExtras.cmake")
            fin = open(file_name, "rt")
            lines = fin.readlines()
            fin.close()
            fin = open(file_name, "wt")
            pattern = re.compile(r'_qt5gui_find_extra_libs\((\S+)\s\"([^\"]+)\".+\)')
            for line in lines:
                match = pattern.search(line)
                if match and len(match.groups()) == 2 and os.path.isabs(match.group(2)):
                    lib_name = os.path.basename(match.group(2))[:-2]
                    lib_name = os.path.splitext(lib_name)[0]
                    other_lib_name = lib_name.replace("lib", "")
                    replace = '_qt5gui_find_extra_libs(%s "%s;%s" "${ANDROID_SYSTEM_LIBRARY_PATH}/usr/lib" "")' % (
                    match.group(1), lib_name, other_lib_name)
                    line = line[:match.start(0)] + replace + line[match.end(0):]
                    fin.write(line)
                else:
                    fin.write(line)
            fin.close()
            if tools.os_info.is_windows:
                self.copy("libgcc_s_seh-1.dll", dst="bin", src=os.path.join(self.deps_env_info['msys2'].MSYS_ROOT, "mingw64", "bin"))
                self.copy("libstdc++-6.dll", dst="bin", src=os.path.join(self.deps_env_info['msys2'].MSYS_ROOT, "mingw64", "bin"))
                self.copy("libwinpthread-1.dll", dst="bin", src=os.path.join(self.deps_env_info['msys2'].MSYS_ROOT, "mingw64", "bin"))

    def package_id(self):
        self.info.include_build_settings()

    def package_info(self):
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.PATH.append(os.path.join(self.package_folder, "qttools", "bin"))
