BUNDLE         = CJKAnchorPlacement.glyphsTool
REPORTER_BUNDLE = CJKAnchorPlacementBatch.glyphsReporter

SDK_GENERAL_BINARY = /Users/palf/Documents/Glyphs_plugins/GlyphsSDK/Python Templates/General Plugin/____PluginName____.glyphsPlugin/Contents/MacOS/plugin

.PHONY: all
all: $(BUNDLE)/Contents/_CodeSignature/CodeResources $(REPORTER_BUNDLE)/Contents/Resources/InspectorView.nib

.PHONY: $(BUNDLE)
$(BUNDLE): $(BUNDLE)/Contents/_CodeSignature/CodeResources

SRC := $(shell find $(BUNDLE) -name '*.py')
$(BUNDLE)/Contents/_CodeSignature/CodeResources: $(SRC)
	-command -v postbuild-codesign >/dev/null 2>&1 && postbuild-codesign $(BUNDLE)
	-command -v postbuild-notarize >/dev/null 2>&1 && postbuild-notarize $(BUNDLE)

.PHONY: $(REPORTER_BUNDLE)
$(REPORTER_BUNDLE): $(REPORTER_BUNDLE)/Contents/MacOS/plugin $(REPORTER_BUNDLE)/Contents/Resources/InspectorView.nib

$(REPORTER_BUNDLE)/Contents/MacOS/plugin: $(SDK_GENERAL_BINARY)
	cp $< $@

$(REPORTER_BUNDLE)/Contents/Resources/InspectorView.nib: $(REPORTER_BUNDLE)/Contents/Resources/InspectorView.xib
	ibtool --compile $@ $<

.PHONY: clean
clean:
	rm -rf $(BUNDLE)/Contents/_CodeSignature
	rm -rf $(REPORTER_BUNDLE)/Contents/Resources/InspectorView.nib
