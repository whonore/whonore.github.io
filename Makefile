SHELL := /bin/bash

BUILD ?= build
INSTALL ?= www

ifeq ($(BUILD),)
$(error BUILD cannot be empty)
endif
ifeq ($(INSTALL),)
$(error INSTALL cannot be empty)
endif

ICONS := $(addprefix $(BUILD)/,favicon.ico favicon-512.png favicon-192.png apple-touch-icon.png)
ICON_MANIFEST := $(BUILD)/manifest.webmanifest

MAP := $(BUILD)/assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 1600
MAPHEIGHT := 800

PHOTOS := $(addprefix $(BUILD)/,$(wildcard assets/photos/*/*.jpg))
PHOTOS_FULL := $(addsuffix -full.jpg,$(basename $(PHOTOS)))
PHOTO_MANIFESTS := $(addprefix $(BUILD)/,assets/photos/manifest.json $(wildcard assets/*/*/manifest.json))
PHOTO_WIDTH := 1024
PHOTO_HEIGHT := 680
PHOTO_QUALITY := 60

PUBS := $(addprefix $(BUILD)/,$(wildcard assets/pubs/*.json))
PUB_MEDIA := $(addprefix $(BUILD)/,$(wildcard assets/pubs/*.pdf) $(wildcard assets/pubs/*.mp4))

MUSIC := $(addprefix $(BUILD)/,$(wildcard assets/music/*.json))
MUSIC_MEDIA := $(addprefix $(BUILD)/,$(wildcard assets/music/*.m4a assets/music/*.jpg))

PROJECTS := $(addprefix $(BUILD)/,$(wildcard assets/projects/*.json))
PROJECT_THUMBS := $(addprefix $(BUILD)/,$(wildcard assets/projects/thumbs/*.jpg))
THUMB_WIDTH := 400
THUMB_HEIGHT := 400
THUMB_QUALITY := 60

ASSETS := $(ICONS) $(ICON_MANIFEST) \
	  $(MAP) $(PHOTOS) $(PHOTOS_FULL) $(PHOTO_MANIFESTS) \
	  $(PUBS) $(PUB_MEDIA) \
	  $(MUSIC) $(MUSIC_MEDIA) \
	  $(PROJECTS) $(PROJECT_THUMBS)

PLACES := $(notdir $(filter-out %.json,$(wildcard assets/photos/*)))
PHOTOS_THTML := $(addprefix $(BUILD)/src/photos/,$(addsuffix .thtml,$(PLACES)))
PHOTOS_HTML := $(patsubst %.thtml,%.html,$(PHOTOS_THTML))

THTML := $(addprefix $(BUILD)/,$(patsubst %.thtml,%.html,$(wildcard src/*.thtml src/projects/*.thtml)))

GEN_HTML := $(THTML) $(PHOTOS_THTML)
COPY_HTML := $(addprefix $(BUILD)/,$(wildcard *.html src/*.html))
HTML := $(GEN_HTML) $(COPY_HTML)

CSS := $(addprefix $(BUILD)/,$(wildcard src/*.css))

INSTALL_EXTS := html css jpg png ico mp4 m4a pdf webmanifest
INSTALL_PAT := $(addprefix -o -name '*.,$(addsuffix ',$(INSTALL_EXTS)))
IGNORE_INSTALL := assets/generated

MINIFY_FLAGS := --html-keep-whitespace \
		--html-keep-end-tags \
		--html-keep-document-tags \
		--html-keep-comments
SVGCLEAN_FLAGS := --remove-invisible-elements=no \
		  --remove-nonsvg-attributes=no \
		  --remove-title=no \
		  --remove-unreferenced-ids=no \
		  --remove-unresolved-classes=no \
		  --remove-unused-defs=no \
		  --trim-ids=no
POSTCSS_FLAGS := --no-map

.PHONY: all install

all: $(ASSETS) $(HTML) $(CSS)

install: all
	for f in $$(find $(BUILD) \
		-path $(addprefix $(BUILD)/,$(IGNORE_INSTALL)) -prune \
		-o -type f \( -false $(INSTALL_PAT) \) -print \
	); do \
		out=$${f/#$(BUILD)/$(INSTALL)}; \
		mkdir -p $$(dirname $$out); \
		cp $$f $$out; \
	done

# THTML

$(MAP): $(MAPDATA) $(PHOTOS_HTML) scripts/build-map.py
	@mkdir -p $(@D)
	scripts/build-map.py - $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^) \
		| svgcleaner $(SVGCLEAN_FLAGS) -c - > $@

$(BUILD)/src/photos/%.thtml: src/photos/_photos.thtml.tmpl $(PHOTO_MANIFESTS) scripts/build-photos.py
	@mkdir -p $(@D)
	scripts/build-photos.py $(notdir $(basename $@)) $(BUILD)

$(BUILD)/%.thtml: %.thtml
	@mkdir -p $(@D)
	cp $< $@

# HTML

$(BUILD)/src/photos/%.html.unmin: $(BUILD)/src/photos/%.thtml scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/src/photos.html.unmin: $(BUILD)/src/photos.thtml $(MAP) $(PHOTO_MANIFESTS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/src/pubs.html.unmin: $(BUILD)/src/pubs.thtml $(PUBS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/src/music.html.unmin: $(BUILD)/src/music.thtml $(MUSIC) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/src/projects.html.unmin: $(BUILD)/src/projects.thtml $(PROJECTS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/src/projects/%.html.unmin: $(BUILD)/src/projects/%.thtml $(PROJECTS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/%.html.unmin: %.thtml scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD)/%.html.unmin: %.html
	@mkdir -p $(@D)
	cp $< $@

$(BUILD)/%.html: $(BUILD)/%.html.unmin
	@mkdir -p $(@D)
	minify --type html $(MINIFY_FLAGS) --output $@ $<

# CSS

$(BUILD)/%.css.unmin: %.css
	@mkdir -p $(@D)
	postcss $(POSTCSS_FLAGS) --output $@ $<

$(BUILD)/%.css: $(BUILD)/%.css.unmin
	@mkdir -p $(@D)
	minify --type css $(MINIFY_FLAGS) --output $@ $<

# JPG

$(BUILD)/%-full.jpg: %.jpg
	@mkdir -p $(@D)
	cp $< $@

$(BUILD)/assets/projects/thumbs/%.jpg: assets/projects/thumbs/%.jpg
	@mkdir -p $(@D)
	convert \
		-strip -interlace Plane -quality $(THUMB_QUALITY) \
		-resize $(THUMB_WIDTH)x$(THUMB_HEIGHT) -auto-orient \
		$< $@

$(BUILD)/%.jpg: %.jpg
	@mkdir -p $(@D)
	convert \
		-strip -interlace Plane -quality $(PHOTO_QUALITY) \
		-resize $(PHOTO_WIDTH)x$(PHOTO_HEIGHT) -auto-orient \
		$< $@

# ICO

$(BUILD)/favicon.ico: $(BUILD)/assets/generated/favicon-32.png $(BUILD)/assets/generated/favicon-16.png
	@mkdir -p $(@D)
	convert $^ $@

# PNG

$(BUILD)/assets/generated/favicon-%.png: assets/icons/favicon.png
	@mkdir -p $(@D)
	convert -sample $*x$* $< $@

$(BUILD)/favicon-%.png: $(BUILD)/assets/generated/favicon-%.png
	@mkdir -p $(@D)
	cp $< $@

$(BUILD)/apple-touch-icon.png: $(BUILD)/assets/generated/favicon-180.png
	@mkdir -p $(@D)
	cp $< $@

# PDF

$(BUILD)/%.pdf: %.pdf
	@mkdir -p $(@D)
	cp $< $@

# MP4

$(BUILD)/%.mp4: %.mp4
	@mkdir -p $(@D)
	cp $< $@

# M4A

$(BUILD)/%.m4a: %.m4a
	@mkdir -p $(@D)
	cp $< $@

# JSON

$(BUILD)/%.json: %.json
	@mkdir -p $(@D)
	cp $< $@

$(BUILD)/%.webmanifest: %.webmanifest
	@mkdir -p $(@D)
	cp $< $@

clean:
	rm -rf $(BUILD) $(INSTALL)
