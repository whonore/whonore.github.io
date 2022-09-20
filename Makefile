BUILD_DIR ?= build
INSTALL_DIR ?= www

ifeq ($(BUILD_DIR),)
$(error BUILD_DIR cannot be empty)
endif
ifeq ($(INSTALL_DIR),)
$(error INSTALL_DIR cannot be empty)
endif

MAP := $(BUILD_DIR)/assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 1600
MAPHEIGHT := 800

PHOTOS := $(addprefix $(BUILD_DIR)/,$(wildcard assets/photos/*/*.jpg))
MANIFESTS := $(addprefix $(BUILD_DIR)/,$(wildcard assets/**/manifest.json))
PHOTO_SIZE := 1024

ASSETS := $(MAP) $(PHOTOS) $(MANIFESTS)

PLACES := $(notdir $(filter-out %.json,$(wildcard assets/photos/*)))
PHOTOS_THTML := $(addprefix $(BUILD_DIR)/src/photos/,$(addsuffix .thtml,$(PLACES)))
PHOTOS_HTML := $(patsubst %.thtml,%.html,$(PHOTOS_THTML))

THTML := $(addprefix $(BUILD_DIR)/,$(patsubst %.thtml,%.html,$(wildcard src/*.thtml)))

GEN_HTML := $(THTML) $(PHOTOS_THTML)
COPY_HTML := $(addprefix $(BUILD_DIR)/,$(wildcard *.html src/*.html))
HTML := $(GEN_HTML) $(COPY_HTML)

CSS := $(addprefix $(BUILD_DIR)/,$(wildcard src/*.css))

.PHONY: all install

all: $(ASSETS) $(HTML) $(CSS)

install: all
	for f in $$(find $(BUILD_DIR) -type f -name '*.html' -o -name '*.css' -o -name '*.jpg'); do \
		out=$${f/#$(BUILD_DIR)/$(INSTALL_DIR)}; \
		mkdir -p $$(dirname $$out); \
		cp $$f $$out; \
	done

$(MAP): $(MAPDATA) $(PHOTOS_HTML) scripts/build-map.py
	@mkdir -p $(@D)
	scripts/build-map.py - $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^) \
		| svgcleaner --remove-title=no --remove-unresolved-classes=no -c - > $@

$(BUILD_DIR)/src/photos/%.thtml: src/photos/_photos.thtml.tmpl scripts/build-photos.py
	@mkdir -p $(@D)
	scripts/build-photos.py $(notdir $(basename $@)) $(BUILD_DIR)

$(BUILD_DIR)/%.thtml: %.thtml
	@mkdir -p $(@D)
	cp $< $@

$(BUILD_DIR)/src/photos/%.html.unmin: $(BUILD_DIR)/src/photos/%.thtml scripts/thtml.py
	@mkdir -p $(@D)
	scripts/thtml.py $< $@

$(BUILD_DIR)/src/photos.html.unmin: $(BUILD_DIR)/src/photos.thtml $(MAP) $(MANIFESTS) scripts/thtml.py
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

$(BUILD_DIR)/%.jpg: %.jpg
	@mkdir -p $(@D)
	@cp $< $@
	mogrify -resize $(PHOTO_SIZE) -auto-orient $@
	jpegoptim --max=60 --all-progressive --strip-all --keep-exif $@

$(BUILD_DIR)/%.json: %.json
	@mkdir -p $(@D)
	cp $< $@
