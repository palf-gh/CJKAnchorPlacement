# encoding: utf-8

from __future__ import division, print_function, unicode_literals

import objc
from GlyphsApp import (Glyphs, GSAnchor, GSCallbackHandler,
                       UPDATEINTERFACE)
from GlyphsApp.plugins import ReporterPlugin
from AppKit import (NSBundle, NSNib, NSNumberFormatter, NSValueTransformer,
                    NSFont, NSColor, NSMakeRect, NSBezierPath, NSBeep,
                    NSScanner, NSGraphicsContext)
from Foundation import NSNumber, NSObject, NSPoint, NSMakeRect as _NSMakeRect


REFERENCE_MODE_BODY = 'body'
REFERENCE_MODE_BBOX = 'bbox'
REFERENCE_MODE_DEFAULTS_KEY = 'CJKAnchorPlacementBatch.ReferenceMode'
DRAWING_DEFAULTS_KEY       = 'CJKAnchorPlacementBatch.DrawingEnabled'

INSPECTOR_CALLBACK_OPERATION = 'GSInspectorViewControllersCallback'

# Centre preview label (match single-glyph tool; not the live edit selection).
PREVIEW_CHARACTER = u'\u3042'  # あ


@objc.python_method
def _mixed_value_placeholder():
    """Short in Latin scripts; full phrase in Japanese (see InspectorView widths)."""
    return Glyphs.localize({
        'en': 'Mixed',
        'de': 'Gemischt',
        'fr': 'Mixte',
        'es': 'Varios',
        'pt': u'Vários',
        'ja': '複数の値',
    })


@objc.python_method
def _missing_value_placeholder():
    return '--'


# ---------------------------------------------------------------------------
# Core geometry  (same semantics as the .glyphsTool, reimplemented)
# ---------------------------------------------------------------------------

def _get_virtual_body_bounds(master, layer):
    vert_width = layer.vertWidth() if callable(layer.vertWidth) else layer.vertWidth
    if vert_width is None:
        vert_width = master.ascender - master.descender
    return _NSMakeRect(0.0, master.ascender - vert_width, layer.width, vert_width)


def _is_valid_bounds(bounds):
    try:
        return bounds.size.width > 0.0 and bounds.size.height > 0.0
    except Exception:
        return False


def _get_reference_bounds(master, layer, reference_mode):
    body = _get_virtual_body_bounds(master, layer)
    if reference_mode != REFERENCE_MODE_BBOX:
        return body if _is_valid_bounds(body) else None
    try:
        bounds = layer.bounds() if callable(layer.bounds) else layer.bounds
    except Exception:
        bounds = None
    return bounds if _is_valid_bounds(bounds) else None


def _bounds_center(b):
    return NSPoint(b.origin.x + b.size.width / 2.0,
                   b.origin.y + b.size.height / 2.0)


def _calc_anchor_position(bounds, mode, name, value):
    c = _bounds_center(bounds)
    min_x, max_x = bounds.origin.x, bounds.origin.x + bounds.size.width
    min_y, max_y = bounds.origin.y, bounds.origin.y + bounds.size.height
    if mode == REFERENCE_MODE_BBOX:
        if name == 'LSB': return NSPoint(min_x - value, c.y)
        if name == 'RSB': return NSPoint(max_x + value, c.y)
        if name == 'TSB': return NSPoint(c.x, max_y + value)
        if name == 'BSB': return NSPoint(c.x, min_y - value)
    else:
        if name == 'LSB': return NSPoint(min_x + value, c.y)
        if name == 'RSB': return NSPoint(max_x - value, c.y)
        if name == 'TSB': return NSPoint(c.x, max_y - value)
        if name == 'BSB': return NSPoint(c.x, min_y + value)
    return None


def _calc_anchor_distance(bounds, mode, name, position):
    min_x, max_x = bounds.origin.x, bounds.origin.x + bounds.size.width
    min_y, max_y = bounds.origin.y, bounds.origin.y + bounds.size.height
    if mode == REFERENCE_MODE_BBOX:
        if name == 'LSB': return min_x - position.x
        if name == 'RSB': return position.x - max_x
        if name == 'TSB': return position.y - max_y
        if name == 'BSB': return min_y - position.y
    else:
        if name == 'LSB': return position.x - min_x
        if name == 'RSB': return max_x - position.x
        if name == 'TSB': return max_y - position.y
        if name == 'BSB': return position.y - min_y
    return None


def _upsert_anchor(layer, name, position):
    anchor = layer.anchors[name] if layer.anchors else None
    if not anchor:
        anchor = GSAnchor(name, NSPoint(0.0, 0.0))
        layer.anchors.append(anchor)
    anchor.position = position


def _read_anchor_values(master, layer, mode):
    """Return (lsb, rsb, tsb, bsb) floats or None per anchor."""
    bounds = _get_reference_bounds(master, layer, mode)
    if bounds is None:
        return None, None, None, None
    result = []
    for name in ('LSB', 'RSB', 'TSB', 'BSB'):
        anchor = layer.anchors[name] if layer.anchors else None
        if anchor:
            try:
                result.append(_calc_anchor_distance(bounds, mode, name, anchor.position))
            except Exception:
                result.append(None)
        else:
            result.append(None)
    return tuple(result)


def _draw_metrics_rect(bounds, mode, lsb, rsb, tsb, bsb, scale, dotted=False):
    min_x, max_x = bounds.origin.x, bounds.origin.x + bounds.size.width
    min_y, max_y = bounds.origin.y, bounds.origin.y + bounds.size.height
    if mode == REFERENCE_MODE_BBOX:
        x1 = min_x - (lsb or 0.0)
        x2 = max_x + (rsb or 0.0)
        y1 = max_y + (tsb or 0.0)
        y2 = min_y - (bsb or 0.0)
    else:
        x1 = min_x + (lsb or 0.0)
        x2 = max_x - (rsb or 0.0)
        y1 = max_y - (tsb or 0.0)
        y2 = min_y + (bsb or 0.0)
    path = NSBezierPath.bezierPathWithRect_(NSMakeRect(x1, y2, x2 - x1, y1 - y2))
    lw = 1.0 / scale
    path.setLineWidth_(lw)
    if dotted:
        path.setLineDash_count_phase_([lw * 3.0, lw * 3.0], 2, 0.0)
    path.stroke()


def _stroke_color_for_values(lsb, rsb, tsb, bsb):
    vals = (lsb, rsb, tsb, bsb)
    none_count = sum(1 for v in vals if v is None)
    if none_count == 4:
        return NSColor.colorWithDeviceRed_green_blue_alpha_(0.0, 159/255.0, 227/255.0, 1.0), True
    h_unbalanced = sum(1 for v in (lsb, rsb) if v is None) == 1
    v_unbalanced = sum(1 for v in (tsb, bsb) if v is None) == 1
    if h_unbalanced or v_unbalanced:
        return NSColor.colorWithDeviceRed_green_blue_alpha_(230/255.0, 0.0, 126/255.0, 1.0), False
    return NSColor.colorWithDeviceRed_green_blue_alpha_(0.0, 159/255.0, 227/255.0, 1.0), False


# ---------------------------------------------------------------------------
# Helper classes referenced by the nib
# ---------------------------------------------------------------------------

class CJKAnchorPlacementBatchNumberFormatter(NSNumberFormatter):

    def isPartialStringValid_newEditingString_errorDescription_(self, partialString, newString, error):
        if len(partialString) == 0:
            return True
        scanner = NSScanner.scannerWithString_(partialString)
        if scanner.scanInt_(None) and scanner.isAtEnd():
            return True
        NSBeep()
        return False


class CJKAnchorPlacementBatchValueTransformer(NSValueTransformer):

    @classmethod
    def transformedValueClass(cls):
        return NSNumber

    @classmethod
    def allowsReverseTransformation(cls):
        return True

    def transformedValue_(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def reverseTransformedValue_(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None


GSInspectorView = objc.lookUpClass('GSInspectorView')


class CJKAnchorPlacementBatchInspectorView(GSInspectorView):

    def acceptsFirstResponder(self):
        return True


class CJKAnchorPlacementBatchInspectorController(NSObject):
    """Supplies `-view` for the inspector without overriding `BaseReporterPlugin.view`."""

    def initWithBatchPlugin_(self, plugin):
        self = objc.super(CJKAnchorPlacementBatchInspectorController, self).init()
        if self is None:
            return None
        # PyObjC plugin instances are not weakref-able; keep a strong ref (paired
        # with the plugin's strong ref to this controller, one pair per reporter).
        self._batchPlugin = plugin
        return self

    def view(self):
        self._batchPlugin._loadNibIfNeeded()
        return self._batchPlugin.inspectorDialogView


# ---------------------------------------------------------------------------
# Main plugin
# ---------------------------------------------------------------------------

class CJKAnchorPlacementBatchPlugin(ReporterPlugin):

    inspectorDialog     = objc.IBOutlet()
    inspectorDialogView = objc.IBOutlet()
    exampleCharacterTextField    = objc.IBOutlet()
    referenceModeSegmentedControl = objc.IBOutlet()
    LSBTextField = objc.IBOutlet()
    RSBTextField = objc.IBOutlet()
    TSBTextField = objc.IBOutlet()
    BSBTextField = objc.IBOutlet()

    LSBValue      = objc.object_property()
    RSBValue      = objc.object_property()
    TSBValue      = objc.object_property()
    BSBValue      = objc.object_property()
    ReferenceMode = objc.object_property()

    @objc.python_method
    def settings(self):
        self.menuName = 'CJK Anchor Placement Batch'

    @objc.python_method
    def start(self):
        self._isApplyingChanges = False
        self._isRefreshingUI    = False

        self._LSBValue      = None
        self._RSBValue      = None
        self._TSBValue      = None
        self._BSBValue      = None
        self._ReferenceMode = self._normalizeMode(
            Glyphs.defaults[REFERENCE_MODE_DEFAULTS_KEY])

        # drawing enabled by default if key is absent
        if Glyphs.defaults[DRAWING_DEFAULTS_KEY] is None:
            Glyphs.defaults[DRAWING_DEFAULTS_KEY] = True

        try:
            GSCallbackHandler.addCallback_forOperation_(
                self, INSPECTOR_CALLBACK_OPERATION)
        except Exception:
            pass

        Glyphs.addCallback(self.refresh_, UPDATEINTERFACE)
        self._inspectorController = None

    @objc.python_method
    def __del__(self):
        try:
            GSCallbackHandler.removeCallback_forOperation_(
                self, INSPECTOR_CALLBACK_OPERATION)
        except Exception:
            pass
        try:
            Glyphs.removeCallback(self.refresh_, UPDATEINTERFACE)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Drawing
    # -----------------------------------------------------------------------

    @objc.python_method
    def background(self, layer):
        self._drawLayer(layer, {'Scale': self.getScale()}, alpha=1.0)

    @objc.python_method
    def inactiveLayerBackground(self, layer):
        # Text tool: show metrics on every glyph in the line; other tools: only
        # the active (edited) glyph via `background`.
        if not self._isTextToolActive():
            return
        self._drawLayer(layer, {'Scale': self.getScale()}, alpha=0.4)

    @objc.python_method
    def _isTextToolActive(self):
        try:
            font = Glyphs.font
            if font is None:
                return False
            return getattr(font, 'tool', None) == 'TextTool'
        except Exception:
            return False

    @objc.python_method
    def _isActiveReporter(self):
        try:
            return self in list(Glyphs.activeReporters)
        except Exception:
            return False

    @objc.python_method
    def _drawLayer(self, layer, info, alpha=1.0):
        if not Glyphs.defaults[DRAWING_DEFAULTS_KEY]:
            return
        try:
            font = layer.parent.parent
            master = font.masters[layer.associatedMasterId or layer.layerId]
        except Exception:
            return
        bounds = _get_reference_bounds(master, layer, self._ReferenceMode)
        if bounds is None:
            return
        lsb, rsb, tsb, bsb = _read_anchor_values(master, layer, self._ReferenceMode)
        scale = info.get('Scale', 1.0)
        color, dotted = _stroke_color_for_values(lsb, rsb, tsb, bsb)
        ctx = NSGraphicsContext.currentContext()
        ctx.saveGraphicsState()
        try:
            color.colorWithAlphaComponent_(alpha).setStroke()
            _draw_metrics_rect(bounds, self._ReferenceMode,
                               lsb, rsb, tsb, bsb, scale, dotted)
        finally:
            ctx.restoreGraphicsState()

    # -----------------------------------------------------------------------
    # Inspector / nib
    # -----------------------------------------------------------------------

    @objc.python_method
    def _tearDownInspectorIfNeeded(self):
        """Clear nib outlets after the inspector is dismissed (reporter off)."""
        self._inspectorController = None
        self.inspectorDialog = None
        self.inspectorDialogView = None
        self.exampleCharacterTextField = None
        self.referenceModeSegmentedControl = None
        self.LSBTextField = None
        self.RSBTextField = None
        self.TSBTextField = None
        self.BSBTextField = None

    def inspectorViewControllersForLayer_(self, layer):
        if not self._isActiveReporter():
            self._tearDownInspectorIfNeeded()
            return []
        if self._inspectorController is None:
            self._inspectorController = (
                CJKAnchorPlacementBatchInspectorController.alloc()
                .initWithBatchPlugin_(self))
        return [self._inspectorController]

    @objc.python_method
    def _loadNibIfNeeded(self):
        if self.inspectorDialogView is not None:
            return
        import os
        bundle_path = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bundle = NSBundle.bundleWithPath_(bundle_path)
        nib = NSNib.alloc().initWithNibNamed_bundle_('InspectorView', bundle)
        nib.instantiateWithOwner_topLevelObjects_(self, None)
        if self.exampleCharacterTextField is not None:
            self.exampleCharacterTextField.setFont_(NSFont.boldSystemFontOfSize_(24.0))
        self._updateReferenceModeControl()
        if self.LSBTextField and self.RSBTextField and self.TSBTextField and self.BSBTextField:
            self.LSBTextField.setNextKeyView_(self.RSBTextField)
            self.RSBTextField.setNextKeyView_(self.TSBTextField)
            self.TSBTextField.setNextKeyView_(self.BSBTextField)
            self.BSBTextField.setNextKeyView_(self.LSBTextField)
        self.refresh_(None)

    # -----------------------------------------------------------------------
    # Selection & refresh
    # -----------------------------------------------------------------------

    @objc.python_method
    def _selectedLayers(self):
        font = Glyphs.font
        if font is None:
            return []
        try:
            layers = font.selectedLayers or []
        except Exception:
            return []
        # Do not dedupe by layer.layerId: every glyph's master layer shares that ID,
        # so text multi-selection would collapse to a single layer.
        seen, out = set(), []
        for layer in layers:
            if layer is None:
                continue
            lid = id(layer)
            if lid in seen:
                continue
            seen.add(lid)
            out.append(layer)
        return out

    @objc.python_method
    def _normalizeMode(self, value):
        return REFERENCE_MODE_BBOX if value == REFERENCE_MODE_BBOX else REFERENCE_MODE_BODY

    @objc.python_method
    def _updateReferenceModeControl(self):
        if self.referenceModeSegmentedControl:
            self.referenceModeSegmentedControl.setSelectedSegment_(
                1 if self._ReferenceMode == REFERENCE_MODE_BBOX else 0)

    def refresh_(self, sender):
        if self.inspectorDialogView is None:
            return
        if not self._isActiveReporter():
            return
        if self._isApplyingChanges or self._isRefreshingUI:
            return
        self._isRefreshingUI = True
        try:
            self._refreshUI()
        finally:
            self._isRefreshingUI = False

    @objc.python_method
    def _refreshUI(self):
        layers = self._selectedLayers()
        count  = len(layers)
        if count == 0:
            self._setFieldsEnabled(False)
            self._setAggregateStates({n: ('missing', None)
                                      for n in ('LSB', 'RSB', 'TSB', 'BSB')})
            if self.exampleCharacterTextField:
                self.exampleCharacterTextField.setStringValue_(PREVIEW_CHARACTER)
            return

        self._setFieldsEnabled(True)
        per = {'LSB': [], 'RSB': [], 'TSB': [], 'BSB': []}
        for layer in layers:
            try:
                font   = layer.parent.parent
                master = font.masters[layer.associatedMasterId or layer.layerId]
            except Exception:
                for n in per:
                    per[n].append(None)
                continue
            bounds = _get_reference_bounds(master, layer, self._ReferenceMode)
            for name in ('LSB', 'RSB', 'TSB', 'BSB'):
                if bounds is None:
                    per[name].append(None)
                    continue
                anchor = layer.anchors[name] if layer.anchors else None
                if not anchor:
                    per[name].append(None)
                    continue
                try:
                    v = _calc_anchor_distance(bounds, self._ReferenceMode,
                                              name, anchor.position)
                    per[name].append(int(round(v)))
                except Exception:
                    per[name].append(None)

        agg = {}
        n_layers = len(layers)
        for name, vals in per.items():
            resolved = [v for v in vals if v is not None]
            if not resolved:
                agg[name] = ('missing', None)
            elif len(resolved) < n_layers:
                # Some layers lack a value for this anchor — not uniformly the same.
                agg[name] = ('mixed', None)
            elif len(set(resolved)) == 1:
                agg[name] = ('uniform', resolved[0])
            else:
                agg[name] = ('mixed', None)

        self._setAggregateStates(agg)

        if self.exampleCharacterTextField:
            self.exampleCharacterTextField.setStringValue_(PREVIEW_CHARACTER)

    @objc.python_method
    def _setFieldsEnabled(self, enabled):
        for f in (self.LSBTextField, self.RSBTextField,
                  self.TSBTextField, self.BSBTextField):
            if f:
                f.setEnabled_(enabled)

    @objc.python_method
    def _setAggregateStates(self, agg):
        self._isRefreshingUI = True
        try:
            fields = {'LSB': (self.LSBTextField, 'LSBValue'),
                      'RSB': (self.RSBTextField, 'RSBValue'),
                      'TSB': (self.TSBTextField, 'TSBValue'),
                      'BSB': (self.BSBTextField, 'BSBValue')}
            for name, (field, key) in fields.items():
                state, value = agg[name]
                if field and field.cell() is not None:
                    ph = (_mixed_value_placeholder() if state == 'mixed'
                          else _missing_value_placeholder())
                    field.cell().setPlaceholderString_(ph)
                setattr(self, key, value if state == 'uniform' else None)
                if field and state != 'uniform':
                    field.setStringValue_('')
        finally:
            self._isRefreshingUI = False

    # -----------------------------------------------------------------------
    # KVO setters
    # -----------------------------------------------------------------------

    @LSBValue.setter
    def LSBValue(self, value):
        if self._LSBValue == value:
            return
        self._LSBValue = value
        self._applyFromUI('LSB', value)

    @RSBValue.setter
    def RSBValue(self, value):
        if self._RSBValue == value:
            return
        self._RSBValue = value
        self._applyFromUI('RSB', value)

    @TSBValue.setter
    def TSBValue(self, value):
        if self._TSBValue == value:
            return
        self._TSBValue = value
        self._applyFromUI('TSB', value)

    @BSBValue.setter
    def BSBValue(self, value):
        if self._BSBValue == value:
            return
        self._BSBValue = value
        self._applyFromUI('BSB', value)

    @ReferenceMode.setter
    def ReferenceMode(self, value):
        value = self._normalizeMode(value)
        if self._ReferenceMode != value:
            self._ReferenceMode = value
            Glyphs.defaults[REFERENCE_MODE_DEFAULTS_KEY] = value
            self._updateReferenceModeControl()
            self.refresh_(None)

    # -----------------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------------

    @objc.python_method
    def _applyFromUI(self, name, value):
        if self._isRefreshingUI:
            return
        if value is None:
            return
        try:
            value = float(value)
        except Exception:
            return
        if value != value or value in (float('inf'), float('-inf')):
            return
        layers = self._selectedLayers()
        if not layers:
            return
        self._isApplyingChanges = True
        try:
            for layer in layers:
                try:
                    font   = layer.parent.parent
                    master = font.masters[layer.associatedMasterId or layer.layerId]
                    bounds = _get_reference_bounds(master, layer, self._ReferenceMode)
                    if bounds is None:
                        continue
                    pos = _calc_anchor_position(bounds, self._ReferenceMode, name, value)
                    if pos is None:
                        continue
                    _upsert_anchor(layer, name, pos)
                except Exception:
                    continue
        finally:
            self._isApplyingChanges = False
        self.refresh_(None)

    # -----------------------------------------------------------------------
    # IB actions
    # -----------------------------------------------------------------------

    def handleAction_(self, sender):
        transformer = CJKAnchorPlacementBatchValueTransformer.alloc().init()
        which = None
        for n, f in (('LSB', self.LSBTextField), ('RSB', self.RSBTextField),
                     ('TSB', self.TSBTextField), ('BSB', self.BSBTextField)):
            if sender is f:
                which = n
                break
        if which is None:
            return
        s = sender.stringValue()
        if not s:
            self.refresh_(None)
            return
        v = transformer.transformedValue_(s)
        if v is None:
            NSBeep()
            self.refresh_(None)
            return
        self._applyFromUI(which, v)

    def handleReferenceModeAction_(self, sender):
        self.ReferenceMode = (REFERENCE_MODE_BBOX
                              if sender.selectedSegment() == 1
                              else REFERENCE_MODE_BODY)

    @objc.python_method
    def __file__(self):
        return __file__
