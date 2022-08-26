MAP := assets/generated/map.svg
MAPDATA := $(wildcard assets/ne_*.zip)
MAPWIDTH := 800
MAPHEIGHT := 600

ASSETS := $(MAP)
HTML := $(patsubst %.thtml,%.html,$(wildcard src/*.thtml))

.PHONY: all

all: $(ASSETS) $(HTML)

$(MAP): $(MAPDATA) scripts/buildmap.py
	mkdir -p $(@D)
	scripts/buildmap.py $(MAPWIDTH) $(MAPHEIGHT) $(filter %.zip,$^)

src/%.html: src/%.thtml $(ASSETS)
	scripts/thtml.py $<
