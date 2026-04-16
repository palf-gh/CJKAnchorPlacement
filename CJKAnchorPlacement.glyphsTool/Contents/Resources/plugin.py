# encoding: utf-8

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from AppKit import NSApplication, NSGraphicsContext, NSFont, NSColor, NSMakeRect, NSInsetRect, NSMakePoint, NSAlternateKeyMask, NSBeep, NSNumberFormatter, NSValueTransformer, NSLeftMouseDown, NSLeftMouseUp, NSMouseMoved, NSLeftMouseDragged

from Foundation import NSNotFound, NSNumber, NSMutableDictionary
import math
import collections
import contextlib

VALID_EVENT_TYPES = (NSLeftMouseDown, NSLeftMouseUp, NSMouseMoved, NSLeftMouseDragged)
REFERENCE_MODE_BODY = 'body'
REFERENCE_MODE_BBOX = 'bbox'
REFERENCE_MODE_DEFAULTS_KEY = 'CJKAnchorPlacementTool.ReferenceMode'

@contextlib.contextmanager
def currentGraphicsContext(context=None):
    context = context or NSGraphicsContext.currentContext()
    context.saveGraphicsState()
    try:
        yield context
    finally:
        context.restoreGraphicsState()

def upsert_anchor(layer, name, position):
    anchor = layer.anchors[name]
    if not anchor:
        anchor = GSAnchor(name, NSPoint(0.0, 0.0))
        layer.anchors.append(anchor)
    anchor.position = position

def delete_anchor(font, master, layer, name):
    anchor_to_be_deleted = layer.anchors[name]
    if anchor_to_be_deleted:
        del layer.anchors[name]

def get_virtual_body_bounds(master, layer):
    vert_width = layer.vertWidth() if callable(layer.vertWidth) else layer.vertWidth
    if vert_width is None:
        vert_width = master.ascender - master.descender
    return NSMakeRect(0.0, master.ascender - vert_width, layer.width, vert_width)

def is_valid_bounds(bounds):
    try:
        return bounds.size.width > 0.0 and bounds.size.height > 0.0
    except Exception:
        return False

def get_reference_bounds(master, layer, reference_mode=REFERENCE_MODE_BODY):
    body_bounds = get_virtual_body_bounds(master, layer)
    if reference_mode != REFERENCE_MODE_BBOX:
        return body_bounds
    try:
        bounds = layer.bounds() if callable(layer.bounds) else layer.bounds
    except Exception:
        bounds = None
    return bounds if is_valid_bounds(bounds) else body_bounds

def get_bounds_min_x(bounds):
    return bounds.origin.x

def get_bounds_max_x(bounds):
    return bounds.origin.x + bounds.size.width

def get_bounds_min_y(bounds):
    return bounds.origin.y

def get_bounds_max_y(bounds):
    return bounds.origin.y + bounds.size.height

def get_bounds_center(bounds):
    return NSPoint(
        bounds.origin.x + bounds.size.width / 2.0,
        bounds.origin.y + bounds.size.height / 2.0
    )
 
def arrange_anchors(font, master, layer, reference_mode=REFERENCE_MODE_BODY):
    if layer:
        reference_bounds = get_reference_bounds(master, layer, reference_mode)
        center = get_bounds_center(reference_bounds)
        
        lsb_anchor = layer.anchors['LSB'] if layer.anchors else None
        rsb_anchor = layer.anchors['RSB'] if layer.anchors else None
        tsb_anchor = layer.anchors['TSB'] if layer.anchors else None
        bsb_anchor = layer.anchors['BSB'] if layer.anchors else None
        
        for anchor in [lsb_anchor, rsb_anchor]:
            if anchor:
                position = NSPoint(anchor.position.x, center.y)
                if position != anchor.position:
                    anchor.position = position
        for anchor in [tsb_anchor, bsb_anchor]:
            if anchor:
                position = NSPoint(center.x, anchor.position.y)
                if position != anchor.position:
                    anchor.position = position

def calc_anchor_position(reference_bounds, reference_mode, anchor_name, value):
    center = get_bounds_center(reference_bounds)
    min_x = get_bounds_min_x(reference_bounds)
    max_x = get_bounds_max_x(reference_bounds)
    min_y = get_bounds_min_y(reference_bounds)
    max_y = get_bounds_max_y(reference_bounds)
    if reference_mode == REFERENCE_MODE_BBOX:
        if anchor_name == 'LSB':
            return NSPoint(min_x - value, center.y)
        if anchor_name == 'RSB':
            return NSPoint(max_x + value, center.y)
        if anchor_name == 'TSB':
            return NSPoint(center.x, max_y + value)
        if anchor_name == 'BSB':
            return NSPoint(center.x, min_y - value)
    else:
        if anchor_name == 'LSB':
            return NSPoint(min_x + value, center.y)
        if anchor_name == 'RSB':
            return NSPoint(max_x - value, center.y)
        if anchor_name == 'TSB':
            return NSPoint(center.x, max_y - value)
        if anchor_name == 'BSB':
            return NSPoint(center.x, min_y + value)
    return None

def calc_anchor_distance(reference_bounds, reference_mode, anchor_name, position):
    min_x = get_bounds_min_x(reference_bounds)
    max_x = get_bounds_max_x(reference_bounds)
    min_y = get_bounds_min_y(reference_bounds)
    max_y = get_bounds_max_y(reference_bounds)
    if reference_mode == REFERENCE_MODE_BBOX:
        if anchor_name == 'LSB':
            return min_x - position.x
        if anchor_name == 'RSB':
            return position.x - max_x
        if anchor_name == 'TSB':
            return position.y - max_y
        if anchor_name == 'BSB':
            return min_y - position.y
    else:
        if anchor_name == 'LSB':
            return position.x - min_x
        if anchor_name == 'RSB':
            return max_x - position.x
        if anchor_name == 'TSB':
            return max_y - position.y
        if anchor_name == 'BSB':
            return position.y - min_y
    return None

def apply_values_for_anchors(font, master, layer, lsb_value, rsb_value, tsb_value, bsb_value, reference_mode=REFERENCE_MODE_BODY):
    if layer:
        reference_bounds = get_reference_bounds(master, layer, reference_mode)
        if lsb_value is not None:
            upsert_anchor(layer, 'LSB', calc_anchor_position(reference_bounds, reference_mode, 'LSB', lsb_value))
        else:
            delete_anchor(font, master, layer, 'LSB')   
        if rsb_value is not None:
            upsert_anchor(layer, 'RSB', calc_anchor_position(reference_bounds, reference_mode, 'RSB', rsb_value))
        else:
            delete_anchor(font, master, layer, 'RSB')
        if tsb_value is not None:
            upsert_anchor(layer, 'TSB', calc_anchor_position(reference_bounds, reference_mode, 'TSB', tsb_value))
        else:
            delete_anchor(font, master, layer, 'TSB')
        if bsb_value is not None:
            upsert_anchor(layer, 'BSB', calc_anchor_position(reference_bounds, reference_mode, 'BSB', bsb_value))
        else:
            delete_anchor(font, master, layer, 'BSB')

def round_to_grid(value, subdivision=1.0):
    return int(math.floor(value / subdivision + 0.5)) * subdivision if subdivision else value

def make_gray_color():
    return NSColor.colorWithDeviceRed_green_blue_alpha_(0.0 / 256.0, 0.0 / 256.0, 0.0 / 256.0, 0.25)

def make_magenta_color():
    return NSColor.colorWithDeviceRed_green_blue_alpha_(230.0 / 256.0, 0.0 / 256.0, 126.0 / 256.0, 1.0)

def make_cyan_color():
    return NSColor.colorWithDeviceRed_green_blue_alpha_(0.0 / 256.0, 159.0 / 256.0, 227.0 / 256.0, 1.0)

def draw_metrics_rect(font, master, layer, lsb_value, rsb_value, tsb_value, bsb_value, reference_mode=REFERENCE_MODE_BODY, scale=1.0, dotted=False):
    reference_bounds = get_reference_bounds(master, layer, reference_mode)
    min_x = get_bounds_min_x(reference_bounds)
    max_x = get_bounds_max_x(reference_bounds)
    min_y = get_bounds_min_y(reference_bounds)
    max_y = get_bounds_max_y(reference_bounds)
    if reference_mode == REFERENCE_MODE_BBOX:
        x1 = min_x - (lsb_value or 0.0)
        x2 = max_x + (rsb_value or 0.0)
        y1 = max_y + (tsb_value or 0.0)
        y2 = min_y - (bsb_value or 0.0)
    else:
        x1 = min_x + (lsb_value or 0.0)
        x2 = max_x - (rsb_value or 0.0)
        y1 = max_y - (tsb_value or 0.0)
        y2 = min_y + (bsb_value or 0.0)
    
    path = NSBezierPath.bezierPathWithRect_(NSMakeRect(x1, y2, x2 - x1, y1 - y2))
    path.setLineWidth_(1.0 / scale)
    if dotted:
        path.setLineDash_count_phase_([path.lineWidth() * 3.0, path.lineWidth() * 3.0], 2, 0.0)
    path.stroke()

def guess_anchor_direction_and_calc_distance_from_edge(location, master, layer, reference_mode=REFERENCE_MODE_BODY):
    bounds = get_reference_bounds(master, layer, reference_mode)
    center = get_bounds_center(bounds)
    delta  = NSPoint(location.x - center.x, location.y - center.y)
    radians = math.atan2(delta.y, delta.x)
    anchor_name = None
    distance_from_edge = None
    if -(math.pi / 4.0) <= radians <= (math.pi / 4.0):
        anchor_name = 'RSB'
        distance_from_edge = calc_anchor_distance(bounds, reference_mode, anchor_name, location)
    elif  (math.pi / 4.0) <= radians <= (math.pi * (3.0 / 4.0)):
        anchor_name = 'TSB'
        distance_from_edge = calc_anchor_distance(bounds, reference_mode, anchor_name, location)
    elif -(math.pi * (3.0 / 4.0)) <= radians <= -(math.pi / 4.0):
        anchor_name = 'BSB'
        distance_from_edge = calc_anchor_distance(bounds, reference_mode, anchor_name, location)
    else:
        anchor_name = 'LSB'
        distance_from_edge = calc_anchor_distance(bounds, reference_mode, anchor_name, location)
    return anchor_name, distance_from_edge

GSInspectorView = objc.lookUpClass('GSInspectorView')
class CJKAnchorPlacementInspectorView(GSInspectorView):
    
    def acceptsFirstResponder(self):
        return True
    
class CJKAnchorPlacementNumberFormatter(NSNumberFormatter):

    def isPartialStringValid_newEditingString_errorDescription_(self, partialString, newString, error):
        if len(partialString) == 0:
            return True
        scanner = NSScanner.scannerWithString_(partialString)
        if scanner.scanInt_(None) and scanner.isAtEnd():
            return True
        NSBeep()
        return False
        
class CJKAnchorPlacementValueTransformer(NSValueTransformer):

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
        except Exception as e:
            return None

    def reverseTransformedValue_(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except Exception as e:
            return None

class CJKAnchorPlacementTool(SelectTool):
    
    inspectorDialogView = objc.IBOutlet()
    exampleCharacterTextField = objc.IBOutlet()
    referenceModeSegmentedControl = objc.IBOutlet()
    
    LSBValue = objc.object_property()
    RSBValue = objc.object_property()
    TSBValue = objc.object_property()
    BSBValue = objc.object_property()
    ReferenceMode = objc.object_property()
    
    LSBTextField = objc.IBOutlet()
    RSBTextField = objc.IBOutlet()
    TSBTextField = objc.IBOutlet()
    BSBTextField = objc.IBOutlet()


    @objc.python_method
    def start(self):
        self.needs_disable_update_anchors = False
        self.grid_subdivision = 1.0
        self.last_do_kerning = None
        self.last_do_spacing = None
        self.ReferenceMode = self.normalized_reference_mode(Glyphs.defaults[REFERENCE_MODE_DEFAULTS_KEY])
    
    @objc.python_method
    def settings(self):
        self.name = 'CJK Anchor Placement'
        self.loadNib('InspectorView', __file__)
        self.setNextResponder_(self.LSBTextField)
        self.keyboardShortcut = 'n'
        self.LSBTextField.setNextKeyView_(self.RSBTextField)
        self.RSBTextField.setNextKeyView_(self.TSBTextField)
        self.TSBTextField.setNextKeyView_(self.BSBTextField)
        self.BSBTextField.setNextKeyView_(self.LSBTextField)
        
        self.exampleCharacterTextField.setFont_(NSFont.boldSystemFontOfSize_(24.0))
        self.update_reference_mode_segmented_control()
    
    @objc.python_method
    def trigger(self):
        return Glyphs.defaults['.'.join((type(self).__name__.replace('NSKVONotifying_', ''), 'Hotkey'))] or self.keyboardShortcut
    
    def mouseDoubleDown_(self, event):
        view = self.editViewController().graphicView()
        location = view.getActiveLocation_(event)
        layer = view.activeLayer()
        if layer:
            font = layer.parent.parent
            master = font.masters[layer.associatedMasterId or layer.layerId]
            anchor_name, distance_from_edge = guess_anchor_direction_and_calc_distance_from_edge(location, master, layer, self.ReferenceMode)
            if distance_from_edge > 0.0:
                if anchor_name == 'LSB':
                    self.LSBValue = distance_from_edge
                elif anchor_name == 'RSB':
                    self.RSBValue = distance_from_edge
                elif anchor_name == 'TSB':
                    self.TSBValue = distance_from_edge
                elif anchor_name == 'BSB':
                    self.BSBValue = distance_from_edge
                return
        objc.super(CJKAnchorPlacementTool, self).mouseDoubleDown_(event)
    
    @LSBValue.setter
    def LSBValue(self, value):
        if self._LSBValue != value:
            self._LSBValue = value
            self.update_anchors()
    
    @RSBValue.setter    
    def RSBValue(self, value):
        if self._RSBValue != value:
            self._RSBValue = value
            self.update_anchors()
    
    @TSBValue.setter
    def TSBValue(self, value):
        if self._TSBValue != value:
            self._TSBValue = value
            self.update_anchors()
    
    @BSBValue.setter
    def BSBValue(self, value):
        if self._BSBValue != value:
            self._BSBValue = value
            self.update_anchors()

    @objc.python_method
    def normalized_reference_mode(self, value):
        return value if value == REFERENCE_MODE_BBOX else REFERENCE_MODE_BODY

    @ReferenceMode.setter
    def ReferenceMode(self, value):
        value = self.normalized_reference_mode(value)
        if self._ReferenceMode != value:
            self._ReferenceMode = value
            Glyphs.defaults[REFERENCE_MODE_DEFAULTS_KEY] = value
            self.update_reference_mode_segmented_control()
            self.sync_values_for_active_layer()

    @objc.python_method
    def update_reference_mode_segmented_control(self):
        if self.referenceModeSegmentedControl:
            self.referenceModeSegmentedControl.setSelectedSegment_(1 if self.ReferenceMode == REFERENCE_MODE_BBOX else 0)

    @objc.python_method
    def sync_values_for_active_layer(self):
        try:
            layer = self.editViewController().graphicView().activeLayer()
        except Exception:
            layer = None
        if layer:
            font = layer.parent.parent
            master = font.masters[layer.associatedMasterId or layer.layerId]
            self.sync_values(font, master, layer)

    @objc.IBAction
    def handleReferenceModeAction_(self, sender):
        self.ReferenceMode = REFERENCE_MODE_BBOX if sender.selectedSegment() == 1 else REFERENCE_MODE_BODY
            
    @objc.IBAction
    def handleAction_(self, sender):
        # Values needs to be updated manually after modifying value with arrow keys.
        valueTransformer = CJKAnchorPlacementValueTransformer.alloc().init()
        self.LSBValue = valueTransformer.transformedValue_(self.LSBTextField.stringValue())
        self.RSBValue = valueTransformer.transformedValue_(self.RSBTextField.stringValue())
        self.TSBValue = valueTransformer.transformedValue_(self.TSBTextField.stringValue())
        self.BSBValue = valueTransformer.transformedValue_(self.BSBTextField.stringValue())
        self.update_anchors()
    
    @objc.python_method
    def update_anchors(self):
        if not self.needs_disable_update_anchors:
            layer = self.editViewController().graphicView().activeLayer()
            if layer:
                font = layer.parent.parent
                master = font.masters[layer.associatedMasterId or layer.layerId]
                apply_values_for_anchors(font, master, layer, self.LSBValue, self.RSBValue, self.TSBValue, self.BSBValue, self.ReferenceMode)
    
    @objc.python_method
    def sync_values(self, font, master, layer, needs_round=False):
        if layer:
            reference_bounds = get_reference_bounds(master, layer, self.ReferenceMode)
            lsb_anchor = layer.anchors['LSB'] if layer.anchors else None
            rsb_anchor = layer.anchors['RSB'] if layer.anchors else None
            tsb_anchor = layer.anchors['TSB'] if layer.anchors else None
            bsb_anchor = layer.anchors['BSB'] if layer.anchors else None
            self.needs_disable_update_anchors = True
            if lsb_anchor:
                self.LSBValue = round_to_grid(calc_anchor_distance(reference_bounds, self.ReferenceMode, 'LSB', lsb_anchor.position), self.grid_subdivision if needs_round else None)
            else:
                self.LSBValue = None
            if rsb_anchor:
                self.RSBValue = round_to_grid(calc_anchor_distance(reference_bounds, self.ReferenceMode, 'RSB', rsb_anchor.position), self.grid_subdivision if needs_round else None)
            else:
                self.RSBValue = None
            if tsb_anchor and master:
                self.TSBValue = round_to_grid(calc_anchor_distance(reference_bounds, self.ReferenceMode, 'TSB', tsb_anchor.position), self.grid_subdivision if needs_round else None)
            else:
                self.TSBValue = None
            if bsb_anchor and master:
                self.BSBValue = round_to_grid(calc_anchor_distance(reference_bounds, self.ReferenceMode, 'BSB', bsb_anchor.position), self.grid_subdivision if needs_round else None)
            else:
                self.BSBValue = None
            self.needs_disable_update_anchors = False
            if needs_round:
                self.update_anchors() # feedback if rounding is enabled
    
    @objc.python_method
    def update_grid_subdivision(self, event):
        if event:
            flags = event.modifierFlags()
            if flags & NSShiftKeyMask:
                self.grid_subdivision = 10.0
                if flags & NSAlternateKeyMask:
                    self.grid_subdivision *= 0.5
            else:
                self.grid_subdivision = 1.0
        else:
            self.grid_subdivision = 1.0
    
    @objc.python_method
    def background(self, layer):
        font = layer.parent.parent
        master = font.masters[layer.associatedMasterId or layer.layerId]
        event = NSApplication.sharedApplication().currentEvent()
        arrange_anchors(font, master, layer, self.ReferenceMode)
        self.update_grid_subdivision(event)
        self.sync_values(font, master, layer, needs_round=event.type() in VALID_EVENT_TYPES if event else False)
        with currentGraphicsContext() as ctx:
            dotted = False
            has_unbalanced_palt = sum((1 if value is None else 0 for value in (self.LSBValue, self.RSBValue))) == 1
            has_unbalanced_vpal = sum((1 if value is None else 0 for value in (self.TSBValue, self.BSBValue))) == 1
            if sum((1 if value is None else 0 for value in (self.LSBValue, self.RSBValue, self.TSBValue, self.BSBValue))) == 4:
                has_unbalanced_palt, has_unbalanced_vpal = None, None
            if has_unbalanced_palt is None and has_unbalanced_vpal is None:
                dotted = True
                make_cyan_color().setStroke()
            elif has_unbalanced_palt or has_unbalanced_vpal:
                make_magenta_color().setStroke()
            else:
                make_cyan_color().setStroke()
            scale = self.editViewController().graphicView().scale()
            draw_metrics_rect(font, master, layer, self.LSBValue, self.RSBValue, self.TSBValue, self.BSBValue, reference_mode=self.ReferenceMode, scale=scale, dotted=dotted)
    
    @objc.python_method
    def __file__(self):
        return __file__
