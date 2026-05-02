import time
from logger import log_debug
from pyside_overlay import SourceOverlay, TargetOverlay, ensure_qapp

# --- Creating/Retrieving Overlays ---

def create_source_overlay_om(app):
    ensure_qapp()
    if getattr(app, 'source_overlay', None):
        app.source_overlay.close()
    
    res_factor = getattr(app, 'resolution_factor', 1.0)
    color = getattr(app, 'source_colour', '#FFFF99')
    opacity = 0.7 # User preference
    
    app.source_overlay = SourceOverlay(resolution_factor=res_factor, initial_color=color, initial_opacity=opacity)
    
    try: x1, y1, x2, y2 = app.source_area
    except: x1, y1, x2, y2 = 100, 100, 300, 200
        
    sf = app.source_overlay.get_scale_factor()
    sx1, sy1 = round(x1 * sf), round(y1 * sf)
    sx2, sy2 = round(x2 * sf), round(y2 * sf)
        
    app.source_overlay.setGeometry(sx1, sy1, sx2-sx1, sy2-sy1)
    
    # Unconditionally hide the source overlay on startup
    app.source_overlay.hide()

def create_target_overlay_om(app, skip_preservation=False):
    ensure_qapp()
    if getattr(app, 'target_overlay', None):
        app.target_overlay.close()
    
    res_factor = getattr(app, 'resolution_factor', 1.0)
    color = getattr(app, 'target_colour', '#663399')
    opacity = getattr(app, 'target_opacity', 0.85)

    app.target_overlay = TargetOverlay(resolution_factor=res_factor, initial_color=color, initial_opacity=opacity)
    
    try: x1, y1, x2, y2 = app.target_area
    except: x1, y1, x2, y2 = 400, 100, 800, 400
        
    sf = app.target_overlay.get_scale_factor()
    sx1, sy1 = round(x1 * sf), round(y1 * sf)
    sx2, sy2 = round(x2 * sf), round(y2 * sf)
        
    app.target_overlay.setGeometry(sx1, sy1, sx2-sx1, sy2-sy1)
    
    # Update text color if available
    text_color = getattr(app, 'target_text_colour', '#FFFFFF')
    app.target_overlay.update_text_color(text_color)
    
    # Assign the text display back to the engine
    app.translation_text = app.target_overlay.text_display
    
    # Unconditionally hide the target overlay on startup
    app.target_overlay.hide()


# --- Adapters for backend calls ---

def toggle_source_visibility_om(app):
    if hasattr(app, 'source_overlay') and app.source_overlay:
        app.source_overlay.toggle_visibility()

def toggle_target_visibility_om(app):
    if hasattr(app, 'target_overlay') and app.target_overlay:
        app.target_overlay.toggle_visibility()

def load_areas_from_config_om(app):
    try:
        s_area = [int(app.config['Settings'].get(f'source_area_{k}', v)) for k, v in zip(['x1','y1','x2','y2'], ['0','0','200','100'])]
        t_area = [int(app.config['Settings'].get(f'target_area_{k}', v)) for k, v in zip(['x1','y1','x2','y2'], ['200','200','500','400'])]
        
        app.source_area = s_area
        app.source_area_x1, app.source_area_y1, app.source_area_x2, app.source_area_y2 = s_area
        
        app.target_area = t_area
        app.target_area_x1, app.target_area_y1, app.target_area_x2, app.target_area_y2 = t_area

        create_source_overlay_om(app)
        create_target_overlay_om(app)
    except Exception as e:
        log_debug(f"Error loading areas: {e}")
