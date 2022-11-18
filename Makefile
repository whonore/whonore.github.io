BUILD_DIR ?= build
INSTALL_DIR ?= www

ifeq ($(BUILD_DIR),)
$(error BUILD_DIR cannot be empty)
endif
ifeq ($(INSTALL_DIR),)
$(error INSTALL_DIR cannot be empty)
endif

ICONS := $(addprefix $(BUILD_DIR)/,favicon.ico favicon-512.png favicon-192.png apple-touch-icon.png)
ICON_MANIFEST := $(BUILD_DIR)/manifest.webmanifest

MAP := $(BUILD_DIR)/assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 1600
MAPHEIGHT := 800

PHOTOS := $(addprefix $(BUILD_DIR)/,$(wildcard assets/photos/*/*.jpg))
PHOTO_MANIFESTS := $(addprefix $(BUILD_DIR)/,assets/photos/manifest.json $(wildcard assets/*/*/manifest.json))
PHOTO_WIDTH := 1024
PHOTO_HEIGHT := 680
PHOTO_QUALITY := 60

PUBS := $(addprefix $(BUILD_DIR)/,$(wildcard assets/pubs/*.json))
PUB_MEDIA := $(addprefix $(BUILD_DIR)/,$(wildcard assets/pubs/*.pdf) $(wildcard assets/pubs/*.mp4))

MUSIC := $(addprefix $(BUILD_DIR)/,$(wildcard assets/music/*.json))
MUSIC_MEDIA := $(addprefix $(BUILD_DIR)/,$(wildcard assets/music/*.m4a assets/music/*.jpg))

ASSETS := $(ICONS) $(ICON_MANIFEST) \
	  $(MAP) $(PHOTOS) $(PHOTO_MANIFESTS) \
	  $(PUBS) $(PUB_MEDIA) \
	  $(MUSIC) $(MUSIC_MEDIA)

PLACES := $(notdir $(filter-out %.json,$(wildcard assets/photos/*)))
PHOTOS_THTML := $(addprefix $(BUILD_DIR)/src/photos/,$(addsuffix .thtml,$(PLACES)))
PHOTOS_HTML := $(patsubst %.thtml,%.html,$(PHOTOS_THTML))

THTML := $(addprefix $(BUILD_DIR)/,$(patsubst %.thtml,%.html,$(wildcard src/*.thtml)))

GEN_HTML := $(THTML) $(PHOTOS_THTML)
COPY_HTML := $(addprefix $(BUILD_DIR)/,$(wildcard *.html src/*.html))
HTML := $(GEN_HTML) $(COPY_HTML)

CSS := $(addprefix $(BUILD_DIR)/,$(wildcard src/*.css))

IGNORE_INSTALL := assets/generated

.PHONY: all install

all: $(ASSETS) $(HTML) $(CSS)

install: all
	for f in $$(find $(BUILD_DIR) \
		-path $(addprefix $(BUILD_DIR)/,$(IGNORE_INSTALL)) -prune \
		-o -type f \( \
		-name '*.html' \
		-o -name '*.css' \
		-o -name '*.jpg' \
		-o -name '*.png' \
		-o -name '*.ico' \
		-o -name '*.mp4' \
		-o -name '*.m4a' \
		-o -name '*.pdf' \
		-o -name '*.webmanifest' \
		\) -print \
		); do \
		out=$${f/#$(BUILD_DIR)/$(INSTALL_DIR)}; \
		mkdir -p $$(dirname $$out); \
		cp $$f $$out; \
	done

# THTML

$(MAP): $(MAPDATA) $(PHOTOS_HTML) scripts/build-map.py
	@mkdir -p $(@D)
	scripts/build-map.py - $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^) \
		| svgcleaner --remove-title=no --remove-unresolved-classes=no -c - > $@

$(BUILD_DIR)/src/photos/%.thtml: src/photos/_photos.thtml.tmpl $(PHOTO_MANIFESTS) scripts/build-photos.py
	@mkdir -p $(@D)
	scripts/build-photos.py $(notdir $(basename $@)) $(BUILD_DIR)

$(BUILD_DIR)/%.thtml: %.thtml
	@mkdir -p $(@D)
	cp $< $@

# HTML

$(BUILD_DIR)/src/photos/%.html.unmin: $(BUILD_DIR)/src/photos/%.thtml scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/src/photos.html.unmin: $(BUILD_DIR)/src/photos.thtml $(MAP) $(PHOTO_MANIFESTS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/src/pubs.html.unmin: $(BUILD_DIR)/src/pubs.thtml $(PUBS) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/src/music.html.unmin: $(BUILD_DIR)/src/music.thtml $(MUSIC) scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/%.html.unmin: %.thtml scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/%.html.unmin: %.html
	@mkdir -p $(@D)
	cp $< $@

$(BUILD_DIR)/%.html: $(BUILD_DIR)/%.html.unmin
	minify --type html \
          --html-keep-whitespace \
          --html-keep-end-tags \
          --html-keep-document-tags \
          --html-keep-comments \
          --output $@ $<

# CSS

$(BUILD_DIR)/%.css.unmin: %.css
	@mkdir -p $(@D)
	postcss $< --output $@ --no-map

$(BUILD_DIR)/%.css: $(BUILD_DIR)/%.css.unmin
	@mkdir -p $(@D)
	minify --type css \
          --html-keep-whitespace \
          --html-keep-end-tags \
          --html-keep-document-tags \
          --html-keep-comments \
          --output $@ $<

# JPG

$(BUILD_DIR)/%.jpg: %.jpg
	@mkdir -p $(@D)
	@cp $< $@
	mogrify -resize $(PHOTO_WIDTH)x$(PHOTO_HEIGHT) -auto-orient $@
	jpegoptim --max=$(PHOTO_QUALITY) --all-progressive --strip-all --keep-exif $@

# ICO

$(BUILD_DIR)/favicon.ico: $(BUILD_DIR)/assets/generated/favicon-32.png $(BUILD_DIR)/assets/generated/favicon-16.png
	@mkdir -p $(@D)
	convert $^ $@

# PNG

$(BUILD_DIR)/assets/generated/favicon-%.png: assets/icons/favicon.png
	@mkdir -p $(@D)
	convert $< -sample $*x$* $@

$(BUILD_DIR)/favicon-%.png: $(BUILD_DIR)/assets/generated/favicon-%.png
	@mkdir -p $(@D)
	cp $< $@

$(BUILD_DIR)/apple-touch-icon.png: $(BUILD_DIR)/assets/generated/favicon-180.png
	@mkdir -p $(@D)
	cp $< $@

# PDF

$(BUILD_DIR)/%.pdf: %.pdf
	@mkdir -p $(@D)
	cp $< $@

# MP4

$(BUILD_DIR)/%.mp4: %.mp4
	@mkdir -p $(@D)
	cp $< $@

# M4A

$(BUILD_DIR)/%.m4a: %.m4a
	@mkdir -p $(@D)
	cp $< $@

# JSON

$(BUILD_DIR)/%.json: %.json
	@mkdir -p $(@D)
	cp $< $@

$(BUILD_DIR)/%.webmanifest: %.webmanifest
	@mkdir -p $(@D)
	cp $< $@
