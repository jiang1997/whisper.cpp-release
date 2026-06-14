# Multi-platform Whisper.cpp Build System
# Inspired by buzz's cross-platform build approach:
#   - GGML_NATIVE=OFF for portable CPU dispatch (SSE4.2/AVX/AVX2 at runtime)
#   - Vulkan GPU backend on Windows and Linux
#   - CoreML on macOS Apple Silicon
#   - Static linking on Windows, shared on Linux/macOS
#
# Override defaults:
#   WHISPER_VULKAN=0 make build     # CPU-only build
#   WHISPER_COREML=0 make build     # Disable CoreML on macOS ARM
#   GGML_SYCL=1 make build          # Intel SYCL build (requires oneAPI: source setvars.sh)

VERSION := $(shell grep 'project.*whisper.cpp.*VERSION' whisper.cpp/CMakeLists.txt | sed -n 's/.*VERSION \([0-9.]*\).*/\1/p')
$(if $(VERSION),,$(error Could not extract version from whisper.cpp/CMakeLists.txt))

RELEASE_DIR := release
BUILD_DIR := whisper.cpp/build
ARTIFACT_SUFFIX :=

# Platform-specific defaults
ifeq ($(OS), Windows_NT)
	BUILD_SHARED_LIBS := OFF
	GGML_VULKAN ?= 1
	GGML_NATIVE ?= OFF
	CMAKE_EXTRA_FLAGS := -DCMAKE_C_FLAGS="-D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR" -DCMAKE_CXX_FLAGS="-D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR" -DCMAKE_C_COMPILER_WORKS=TRUE -DCMAKE_CXX_COMPILER_WORKS=TRUE
	BIN_EXT := .exe
	ARCHIVE_EXT := .zip
	ARCH := x64
else ifeq ($(shell uname -s), Linux)
	BUILD_SHARED_LIBS := ON
	GGML_VULKAN ?= 1
	GGML_NATIVE ?= OFF
	CMAKE_EXTRA_FLAGS := -DCMAKE_INSTALL_RPATH='$$ORIGIN' -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
	BIN_EXT :=
	ARCHIVE_EXT := .tar.gz
	ARCH := $(shell uname -m)
else ifeq ($(shell uname -s), Darwin)
	BUILD_SHARED_LIBS := ON
	GGML_NATIVE ?= OFF
	ARCH := $(shell uname -m)
	BIN_EXT :=
	ARCHIVE_EXT := .tar.gz
	ifeq ($(ARCH), arm64)
		WHISPER_COREML ?= 1
		GGML_VULKAN ?= 0
	else
		WHISPER_COREML ?= 0
		GGML_VULKAN ?= 0
	endif
	CMAKE_EXTRA_FLAGS :=
endif

ifeq ($(GGML_SYCL), 1)
	GGML_VULKAN := 0
	GGML_SYCL := 1
	ARTIFACT_SUFFIX := -sycl
	CMAKE_EXTRA_FLAGS += -DGGML_SYCL=1 -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx
else
	GGML_SYCL := 0
endif

.PHONY: build clean release

build:
	rm -rf $(BUILD_DIR)
	cmake -S whisper.cpp -B $(BUILD_DIR) \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_SHARED_LIBS=$(BUILD_SHARED_LIBS) \
		-DGGML_VULKAN=$(GGML_VULKAN) \
		-DGGML_SYCL=$(GGML_SYCL) \
		-DGGML_NATIVE=$(GGML_NATIVE) \
		$(if $(WHISPER_COREML),-DWHISPER_COREML=$(WHISPER_COREML)) \
		$(CMAKE_EXTRA_FLAGS)
	cmake --build $(BUILD_DIR) -j --config Release --verbose

release: build
	rm -rf $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
	mkdir -p $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
	cp $(BUILD_DIR)/bin/whisper-cli$(BIN_EXT) $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
	cp $(BUILD_DIR)/bin/whisper-server$(BIN_EXT) $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
ifeq ($(BUILD_SHARED_LIBS), ON)
	cp -P $(BUILD_DIR)/src/libwhisper.* $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/ 2>/dev/null || true
	cp -P $(BUILD_DIR)/ggml/src/libggml* $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/ 2>/dev/null || true
	cp -P $(BUILD_DIR)/ggml/src/ggml-vulkan/libggml-vulkan.so* $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/ 2>/dev/null || true
	cp -P $(BUILD_DIR)/ggml/src/ggml-sycl/libggml-sycl.so* $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/ 2>/dev/null || true
endif
ifeq ($(ARCHIVE_EXT), .zip)
	cd $(RELEASE_DIR) && zip -r whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX).zip whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
else
	cd $(RELEASE_DIR) && tar -czf whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX).tar.gz whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/
endif
	rm -rf $(RELEASE_DIR)/whisper-$(VERSION)-$(ARCH)$(ARTIFACT_SUFFIX)/

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(RELEASE_DIR)
