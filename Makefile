MAP := assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 1600
MAPHEIGHT := 800

ASSETS := $(MAP)
HTML := $(patsubst %.thtml,%.html,$(wildcard src/*.thtml))
TPHOTOS := $(addprefix src/photos/,$(addsuffix .thtml,$(notdir $(filter-out %.json,$(wildcard assets/photos/*)))))
PHOTOS := $(patsubst %.thtml,%.html,$(TPHOTOS))

.PHONY: all

all: $(PHOTOS) $(ASSETS) $(HTML)

$(MAP): $(MAPDATA) $(PHOTOS) scripts/build-map.py
	mkdir -p $(@D)
	scripts/build-map.py - $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^) \
		| svgcleaner --remove-title=no --remove-unresolved-classes=no -c - > $@

src/%.html: src/%.thtml $(ASSETS) scripts/thtml.py
	scripts/thtml.py $<

src/photos/%.thtml: src/photos/_photos.thtml.tmpl scripts/build-photos.py
	scripts/build-photos.py $(notdir $(basename $@))

src/photos/%.html: src/photos/%.thtml scripts/thtml.py
	scripts/thtml.py $<
