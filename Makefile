MAP := assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 1600
MAPHEIGHT := 800

ASSETS := $(MAP)
HTML := $(patsubst %.thtml,%.html,$(wildcard src/*.thtml))

.PHONY: all

all: $(ASSETS) $(HTML)

$(MAP): $(MAPDATA) scripts/build-map.py
	mkdir -p $(@D)
	scripts/build-map.py - $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^) \
		| svgcleaner --remove-title=no --remove-unresolved-classes=no -c - > $@

src/%.html: src/%.thtml $(ASSETS)
	scripts/thtml.py $<
